"""Windows privilege detection and self-elevation helpers.

Every Windows-specific ``ctypes`` call is guarded by an ``is_windows()`` check
and wrapped in try/except so this module imports cleanly on *any* platform
(handy for linting/CI on Linux or macOS).
"""
from __future__ import annotations

import ctypes
import os
import sys


def is_windows() -> bool:
    """True when running on Windows."""
    return os.name == "nt"


def is_admin() -> bool:
    """Return True when the current process holds an elevated admin token.

    Uses ``ctypes.windll.shell32.IsUserAnAdmin()`` exactly as required. Returns
    False on non-Windows platforms or if the check cannot be performed.
    """
    if not is_windows():
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin() -> bool:
    """Relaunch this program elevated via the UAC ``runas`` verb.

    Returns True if the elevation request was *dispatched* (the current,
    non-elevated process should then exit so only the elevated copy remains).
    Returns False if it could not be started — e.g. the user declined the UAC
    prompt, or we are not on Windows.
    """
    if not is_windows():
        return False
    try:
        if getattr(sys, "frozen", False):
            # Packaged by PyInstaller: argv[0] is the .exe itself.
            executable = sys.executable
            params = " ".join(f'"{a}"' for a in sys.argv[1:])
        else:
            # Running under the interpreter: re-pass the script path.
            executable = sys.executable
            script = os.path.abspath(sys.argv[0])
            params = " ".join([f'"{script}"', *[f'"{a}"' for a in sys.argv[1:]]])

        # ShellExecuteW returns a value > 32 on success. SW_SHOWNORMAL == 1.
        rc = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", executable, params, None, 1
        )
        return int(rc) > 32
    except Exception:
        return False
