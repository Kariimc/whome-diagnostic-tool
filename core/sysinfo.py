"""Read the current Windows version straight from the registry.

Fast, synchronous and dependency-free (uses ``winreg``), so the Updates tab can
show a live "this PC is on …" readout and you can confirm when an upgrade landed.
Safe to import and call on any OS.
"""
from __future__ import annotations

import os

_CV_KEY = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"


def get_windows_version() -> dict:
    """Return {product, version, build, summary} for the running Windows.

    ``version`` is the friendly release (e.g. "22H2", or "1903" on older builds
    where Windows stored it as ReleaseId). On non-Windows hosts the summary
    explains that the app is in preview mode.
    """
    info = {"product": "", "version": "", "build": "", "summary": ""}
    if os.name != "nt":
        info["summary"] = "Not running on Windows (preview mode)"
        return info

    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _CV_KEY) as key:
            def val(name: str, default: str = "") -> str:
                try:
                    return str(winreg.QueryValueEx(key, name)[0])
                except OSError:
                    return default

            product = val("ProductName", "Windows")
            # DisplayVersion (20H2+) is friendliest; ReleaseId covers 1903/1909.
            display = val("DisplayVersion") or val("ReleaseId")
            build = val("CurrentBuild")
            ubr = val("UBR")

        # The registry still says "Windows 10" on Windows 11 — correct it.
        try:
            if int(build) >= 22000 and "Windows 10" in product:
                product = product.replace("Windows 10", "Windows 11")
        except ValueError:
            pass

        full_build = f"{build}.{ubr}" if build and ubr else build
        info.update(product=product, version=display, build=full_build)
        parts = [
            product,
            f"Version {display}" if display else "",
            f"build {full_build}" if full_build else "",
        ]
        info["summary"] = " • ".join(p for p in parts if p)
    except Exception as exc:  # noqa: BLE001 - never let a readout crash the UI
        info["summary"] = f"Could not read Windows version ({exc})"
    return info
