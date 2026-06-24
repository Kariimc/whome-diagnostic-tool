"""Asynchronous command executor with real-time output streaming.

This module pipes long-running Windows tools (``sfc``, ``DISM``, ``chkdsk``,
``netsh`` …) into the UI **without blocking it**, using
``asyncio.create_subprocess_exec`` with ``asyncio.subprocess.PIPE``.

Design note — *no UI imports here*. The caller passes an ``emit`` callback that
receives output as it arrives. The console widget supplies that callback. This
keeps the dependency arrow pointing one way (ui -> core) and avoids circular
imports entirely.
"""
from __future__ import annotations

import asyncio
import subprocess
import threading
from typing import Awaitable, Callable, Union

# emit(text) -> None | Awaitable.
# The common case is a *sync* callback (append text to a TextField, then call
# page.update()). Async callbacks are supported too.
Emit = Callable[[str], Union[None, Awaitable[None]]]

# Suppress the brief console window that child processes (cmd, net, sfc …) would
# otherwise flash when spawned from a windowed GUI. 0 (no-op) on non-Windows.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


async def _maybe_await(value) -> None:
    """Await *value* if the emit callback returned a coroutine."""
    if asyncio.iscoroutine(value):
        await value


def _decode(data: bytes) -> str:
    """Best-effort decode of Windows console output.

    ``sfc`` emits UTF-16LE (a NUL byte between ASCII characters); most other
    tools emit the OEM code page (cp850 / cp437). We sniff UTF-16 by NUL
    density first, then fall back through common encodings.
    """
    if not data:
        return ""
    # Heuristic: a high density of NUL bytes means UTF-16LE text.
    if data.count(0) > len(data) // 3:
        try:
            return data.decode("utf-16-le", errors="replace")
        except Exception:
            pass
    for enc in ("utf-8", "cp850", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


async def run_command(
    command: list[str],
    emit: Emit,
    *,
    dry_run: bool = True,
    label: str = "",
) -> int:
    """Run *command*, streaming its output through *emit*. Returns the exit code.

    When ``dry_run`` is True **nothing touches the system**: the command is
    printed and a short simulated run is streamed back so the whole UI can be
    exercised safely. This is the required safety behaviour.
    """
    pretty = " ".join(command)
    if label:
        await _maybe_await(emit(f"\n=== {label} ===\n"))
    await _maybe_await(emit(f"$ {pretty}\n"))

    if dry_run:
        # Required safety net: replace real system commands with a print.
        print(f"DRY RUN: Executing {pretty}")
        await _maybe_await(
            emit("[DRY RUN] Command not executed — Safe Mode is ON.\n")
        )
        for step in ("Initializing", "Scanning", "Verifying", "Finalizing"):
            await asyncio.sleep(0.4)
            await _maybe_await(emit(f"[DRY RUN] {step}...\n"))
        await _maybe_await(emit("[DRY RUN] Completed. Exit code: 0\n"))
        return 0

    # --- real execution ------------------------------------------------
    try:
        return await _run_async(command, emit)
    except NotImplementedError:
        # Some event-loop policies (e.g. the Selector loop) can't spawn
        # subprocesses. Fall back to a worker thread so the tool still works.
        await _maybe_await(emit("[i] Falling back to threaded execution...\n"))
        try:
            return await _run_threaded(command, emit)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
            await _maybe_await(emit(f"\n[error: {exc}]\n"))
            return 1
    except FileNotFoundError:
        await _maybe_await(
            emit(f"\n[error: '{command[0]}' was not found. "
                 "These tools exist on Windows only.]\n")
        )
        return 1
    except Exception as exc:  # noqa: BLE001 - never let a task crash the UI
        await _maybe_await(emit(f"\n[error: {exc}]\n"))
        return 1


async def _run_async(command: list[str], emit: Emit) -> int:
    """Preferred path: native asyncio subprocess with piped stdout."""
    proc = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        creationflags=_NO_WINDOW,
    )
    assert proc.stdout is not None
    # Read fixed-size chunks (not lines) so progress that uses carriage
    # returns — like DISM's percentage — streams through in near real time.
    while True:
        chunk = await proc.stdout.read(1024)
        if not chunk:
            break
        await _maybe_await(emit(_decode(chunk)))
    rc = await proc.wait()
    await _maybe_await(emit(f"\n[exit code: {rc}]\n"))
    return rc


async def _run_threaded(command: list[str], emit: Emit) -> int:
    """Fallback path used only when the loop can't spawn subprocesses.

    A daemon thread reads the pipe and hands chunks back to the asyncio loop via
    ``call_soon_threadsafe``, so the UI keeps updating without blocking.
    """
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    _DONE = object()

    def worker() -> None:
        rc = 1
        try:
            proc = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=_NO_WINDOW,
            )
            assert proc.stdout is not None
            for raw in iter(lambda: proc.stdout.read(1024), b""):
                loop.call_soon_threadsafe(queue.put_nowait, _decode(raw))
            proc.wait()
            rc = proc.returncode
            loop.call_soon_threadsafe(queue.put_nowait, f"\n[exit code: {rc}]\n")
        except Exception as exc:  # noqa: BLE001
            loop.call_soon_threadsafe(queue.put_nowait, f"\n[error: {exc}]\n")
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, (_DONE, rc))

    threading.Thread(target=worker, daemon=True).start()

    while True:
        item = await queue.get()
        if isinstance(item, tuple) and item and item[0] is _DONE:
            return item[1]
        await _maybe_await(emit(item))


async def run_steps(
    steps: list[list[str]],
    emit: Emit,
    *,
    dry_run: bool = True,
    label: str = "",
) -> int:
    """Run a sequence of commands in order, streaming each one's output.

    Used by multi-step tasks (e.g. the Windows Update reset). Continues through
    individual failures — a service that is already stopped, or a cache folder
    that does not exist yet, is expected and must not abort the rest — and
    returns the last non-zero exit code seen (0 if all succeeded).
    """
    if label:
        await _maybe_await(emit(f"\n=== {label} ===\n"))
    overall = 0
    total = len(steps)
    for index, cmd in enumerate(steps, start=1):
        await _maybe_await(emit(f"\n--- step {index}/{total} ---\n"))
        rc = await run_command(list(cmd), emit, dry_run=dry_run, label="")
        if rc != 0:
            overall = rc
    await _maybe_await(emit("\n[sequence finished]\n"))
    return overall


async def execute(task, emit: Emit, *, dry_run: bool = True) -> int:
    """Dispatch a Task to the correct runner.

    Multi-step tasks (``task.steps``) run as a sequence; everything else runs as
    a single command. ``task`` is duck-typed so the executor stays decoupled
    from the tasks module (it only reads ``.steps``, ``.command`` and ``.label``).
    """
    steps = getattr(task, "steps", None)
    if steps:
        return await run_steps(steps, emit, dry_run=dry_run, label=task.label)
    return await run_command(task.command, emit, dry_run=dry_run, label=task.label)
