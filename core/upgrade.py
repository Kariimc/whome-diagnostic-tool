"""Download and launch Microsoft's official Windows 10 Update Assistant.

Powers the one-click "Upgrade to 22H2 now" action. This is the reliable way to
move a PC that is too far behind for Windows Update to catch up on its own
(e.g. stuck on 1903) all the way to the current release, via an in-place upgrade
that keeps files and apps.

The download uses ``curl.exe`` (present on Windows 10 1803+) with a PowerShell
fallback, then launches the signed Microsoft installer (which self-elevates).
Everything is gated by ``dry_run`` so it can be previewed safely, and any
network failure points the user back to the "Open the upgrade page" button.
"""
from __future__ import annotations

import asyncio
import os
import tempfile

from core.admin import is_windows
from core.executor import run_command

# Official Microsoft FWLink behind the "Update now" button on
# https://www.microsoft.com/software-download/windows10  -> Windows10Upgrade*.exe
UPDATE_ASSISTANT_URL = "https://go.microsoft.com/fwlink/?LinkID=799445"
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


async def _say(emit, text: str) -> None:
    result = emit(text)
    if asyncio.iscoroutine(result):
        await result


async def download_and_launch_update_assistant(emit, *, dry_run: bool = True) -> int:
    dest = os.path.join(tempfile.gettempdir(), "Windows10UpgradeAssistant.exe")

    await _say(emit, "\n=== Upgrade to Windows 10 22H2 (Update Assistant) ===\n")
    await _say(emit, f"Source : {UPDATE_ASSISTANT_URL}\n")
    await _say(emit, f"Save to: {dest}\n")

    if dry_run:
        print(f"DRY RUN: download {UPDATE_ASSISTANT_URL} -> {dest} and launch")
        await _say(emit, "[DRY RUN] Would download Microsoft's official Update "
                         "Assistant and launch it.\n")
        await _say(emit, "[DRY RUN] The Assistant would then upgrade Windows in "
                         "place to 22H2, keeping your files and apps.\n")
        await _say(emit, "[DRY RUN] Exit code: 0\n")
        return 0

    if not is_windows():
        await _say(emit, "[error: this action only works on Windows.]\n")
        return 1

    # 1) Download (curl.exe first, then PowerShell as a fallback).
    await _say(emit, "\nDownloading the Update Assistant (~6 MB)...\n")
    rc = await run_command(
        ["curl.exe", "-L", "-f", "-A", _UA, "--retry", "2", "-o", dest,
         UPDATE_ASSISTANT_URL],
        emit, dry_run=False,
    )
    if rc != 0 or not _looks_valid(dest):
        await _say(emit, "[i] curl download failed — retrying with PowerShell...\n")
        rc = await run_command(
            ["powershell", "-NoProfile", "-Command",
             "$ProgressPreference='SilentlyContinue'; "
             f"Invoke-WebRequest -UseBasicParsing -UserAgent '{_UA}' "
             f"-Uri '{UPDATE_ASSISTANT_URL}' -OutFile '{dest}'"],
            emit, dry_run=False,
        )

    if not _looks_valid(dest):
        await _say(emit, "\n[error: could not download the Update Assistant on this "
                         "network. Use the “Open the Windows 10 upgrade page” button "
                         "and click “Update now” there instead.]\n")
        return 1

    await _say(emit, f"Downloaded {os.path.getsize(dest):,} bytes.\n")

    # 2) Launch it. The Assistant is signed by Microsoft and self-elevates; we
    #    request elevation explicitly so the UAC prompt appears right away.
    await _say(emit, "Launching the Update Assistant — follow its on-screen "
                     "prompts to upgrade.\n")
    try:
        import ctypes
        rc2 = ctypes.windll.shell32.ShellExecuteW(None, "runas", dest, None, None, 1)
        if int(rc2) <= 32:
            os.startfile(dest)  # type: ignore[attr-defined]  # noqa: S606
        await _say(emit, "[ok] The Update Assistant is open. Keep the PC plugged "
                         "in — the upgrade can take 30–90 min and reboots a few "
                         "times. Your files and apps are kept.\n")
        return 0
    except Exception as exc:  # noqa: BLE001
        await _say(emit, f"[error launching the Assistant: {exc}]\n")
        return 1


def _looks_valid(path: str) -> bool:
    """A real Update Assistant is a multi-MB exe; reject tiny/error files."""
    try:
        return os.path.exists(path) and os.path.getsize(path) > 500_000
    except OSError:
        return False


# Registry of named actions the executor can dispatch (see core.executor.execute).
ACTIONS = {
    "upgrade_assistant": download_and_launch_update_assistant,
}


async def run_action(key: str, emit, *, dry_run: bool = True) -> int:
    fn = ACTIONS.get(key)
    if fn is None:
        await _say(emit, f"\n[unknown action: {key}]\n")
        return 1
    return await fn(emit, dry_run=dry_run)
