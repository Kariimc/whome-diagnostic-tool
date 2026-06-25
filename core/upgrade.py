"""Download and launch Microsoft's official Windows 10 upgrade tools.

Two one-click actions:

* **Update Assistant** — in-place upgrade of *this* PC to 22H2 (keeps files/apps).
* **Media Creation Tool** — put 22H2 onto a USB thumb drive (8 GB+) or save an
  ISO, for upgrading / repairing / clean-installing.

Both download the signed Microsoft tool (``curl.exe`` with a PowerShell fallback)
and launch it elevated. Everything is gated by ``dry_run`` so it can be previewed
safely, and any network failure points the user back to the manual download page.
"""
from __future__ import annotations

import asyncio
import os
import tempfile

from core.admin import is_windows
from core.executor import run_command

# Official Microsoft FWLinks (the same ones behind the buttons on
# https://www.microsoft.com/software-download/windows10).
UPDATE_ASSISTANT_URL = "https://go.microsoft.com/fwlink/?LinkID=799445"
MEDIA_CREATION_TOOL_URL = "https://go.microsoft.com/fwlink/?LinkId=691209"
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


async def _say(emit, text: str) -> None:
    result = emit(text)
    if asyncio.iscoroutine(result):
        await result


def _looks_valid(path: str) -> bool:
    """A real Microsoft tool is a multi-MB exe; reject tiny/error files."""
    try:
        return os.path.exists(path) and os.path.getsize(path) > 500_000
    except OSError:
        return False


async def _download(url: str, dest: str, emit) -> bool:
    """Download *url* to *dest*; curl.exe first, PowerShell as a fallback."""
    rc = await run_command(
        ["curl.exe", "-L", "-f", "-A", _UA, "--retry", "2", "-o", dest, url],
        emit, dry_run=False,
    )
    if rc == 0 and _looks_valid(dest):
        return True
    await _say(emit, "[i] curl download failed — retrying with PowerShell...\n")
    await run_command(
        ["powershell", "-NoProfile", "-Command",
         "$ProgressPreference='SilentlyContinue'; "
         f"Invoke-WebRequest -UseBasicParsing -UserAgent '{_UA}' "
         f"-Uri '{url}' -OutFile '{dest}'"],
        emit, dry_run=False,
    )
    return _looks_valid(dest)


async def _launch(dest: str, emit) -> int:
    """Launch *dest* elevated (it self-elevates too; runas shows UAC at once)."""
    try:
        import ctypes
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", dest, None, None, 1)
        if int(rc) <= 32:
            os.startfile(dest)  # type: ignore[attr-defined]  # noqa: S606
        return 0
    except Exception as exc:  # noqa: BLE001
        await _say(emit, f"[error launching: {exc}]\n")
        return 1


async def _fetch_and_run(emit, *, dry_run: bool, url: str, filename: str,
                         title: str, dry_lines: list[str], launch_note: str) -> int:
    dest = os.path.join(tempfile.gettempdir(), filename)
    await _say(emit, f"\n=== {title} ===\n")
    await _say(emit, f"Source : {url}\n")
    await _say(emit, f"Save to: {dest}\n")

    if dry_run:
        print(f"DRY RUN: download {url} -> {dest} and launch")
        await _say(emit, "[DRY RUN] Would download the official Microsoft tool and "
                         "launch it.\n")
        for line in dry_lines:
            await _say(emit, f"[DRY RUN] {line}\n")
        await _say(emit, "[DRY RUN] Exit code: 0\n")
        return 0

    if not is_windows():
        await _say(emit, "[error: this action only works on Windows.]\n")
        return 1

    await _say(emit, f"\nDownloading {filename}...\n")
    if not await _download(url, dest, emit):
        await _say(emit, "\n[error: could not download on this network. Use the "
                         "“Open the Windows 10 upgrade page” button and download it "
                         "manually instead.]\n")
        return 1

    await _say(emit, f"Downloaded {os.path.getsize(dest):,} bytes.\n")
    await _say(emit, launch_note + "\n")
    return await _launch(dest, emit)


async def download_and_launch_update_assistant(emit, *, dry_run: bool = True) -> int:
    return await _fetch_and_run(
        emit, dry_run=dry_run,
        url=UPDATE_ASSISTANT_URL,
        filename="Windows10UpgradeAssistant.exe",
        title="Upgrade to Windows 10 22H2 (Update Assistant)",
        dry_lines=[
            "The Assistant would upgrade Windows in place to 22H2, keeping your "
            "files and apps.",
        ],
        launch_note="Launching the Update Assistant — follow its prompts. Keep the "
                    "PC plugged in; the upgrade takes 30–90 min and reboots a few "
                    "times. Your files and apps are kept.",
    )


async def download_and_launch_media_creation_tool(emit, *, dry_run: bool = True) -> int:
    return await _fetch_and_run(
        emit, dry_run=dry_run,
        url=MEDIA_CREATION_TOOL_URL,
        filename="MediaCreationTool22H2.exe",
        title="Create a Windows 10 22H2 USB drive / ISO (Media Creation Tool)",
        dry_lines=[
            "The Media Creation Tool would open. To make a thumb drive:",
            "  1) Accept the license terms.",
            "  2) Choose 'Create installation media (USB flash drive, DVD, or ISO "
            "file) for another PC'.",
            "  3) Pick the language/edition (or keep the recommended options).",
            "  4) Choose 'USB flash drive' and select your stick (8 GB+) — it will "
            "be ERASED. (Or choose 'ISO file' to just save the image.)",
            "It then downloads 22H2 and writes a bootable installer.",
        ],
        launch_note="Launching the Media Creation Tool. Plug in an 8 GB+ USB stick, "
                    "then choose 'Create installation media' → 'USB flash drive' and "
                    "pick your drive (it will be erased). Or pick 'ISO file' to save "
                    "the image to upgrade/repair later.",
    )


# Registry of named actions the executor can dispatch (see core.executor.execute).
ACTIONS = {
    "upgrade_assistant": download_and_launch_update_assistant,
    "media_creation_tool": download_and_launch_media_creation_tool,
}


async def run_action(key: str, emit, *, dry_run: bool = True) -> int:
    fn = ACTIONS.get(key)
    if fn is None:
        await _say(emit, f"\n[unknown action: {key}]\n")
        return 1
    return await fn(emit, dry_run=dry_run)
