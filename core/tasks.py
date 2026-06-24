"""Catalog of diagnostic / repair tasks.

Each :class:`Task` is a *pure data* description — no UI and no execution logic —
so it can be rendered by the dashboard and run by the executor independently.
The commands here are the genuinely useful Windows repair tools.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Category(str, Enum):
    OS_REPAIR = "OS Repair"
    NETWORK = "Network & Runtime"


class Risk(str, Enum):
    READ_ONLY = "read-only"  # only inspects; never changes the system
    REPAIR = "repair"        # modifies system state
    REBOOT = "reboot"        # modifies state and may require a restart


@dataclass(frozen=True)
class Task:
    id: str
    label: str
    description: str
    command: list[str]
    category: Category
    risk: Risk = Risk.READ_ONLY
    requires_admin: bool = True
    est_minutes: str = "1-3 min"

    @property
    def command_str(self) -> str:
        return " ".join(self.command)


# Ordered roughly by "try this first". Commands are passed to
# create_subprocess_exec as argument lists (no shell), so each token is literal.
TASKS: list[Task] = [
    # ---------------------------- OS Repair ----------------------------
    Task(
        "dism_restore", "DISM — Repair Windows image",
        "Downloads healthy files from Windows Update and repairs the component "
        "store (DISM /Online /Cleanup-Image /RestoreHealth). Run this BEFORE SFC "
        "when SFC alone can't fix things.",
        ["DISM", "/Online", "/Cleanup-Image", "/RestoreHealth"],
        Category.OS_REPAIR, Risk.REPAIR, True, "10-30 min",
    ),
    Task(
        "sfc_scan", "SFC — Repair system files",
        "Scans all protected system files and repairs corrupted ones "
        "(sfc /scannow). The go-to fix for crashes, missing DLLs and odd errors.",
        ["sfc", "/scannow"],
        Category.OS_REPAIR, Risk.REPAIR, True, "5-15 min",
    ),
    Task(
        "sfc_verify", "SFC — Verify only (safe)",
        "Checks system-file integrity WITHOUT changing anything "
        "(sfc /verifyonly). A good, non-destructive first diagnostic.",
        ["sfc", "/verifyonly"],
        Category.OS_REPAIR, Risk.READ_ONLY, True, "5-15 min",
    ),
    Task(
        "dism_check", "DISM — Quick health check",
        "Fast check of the component store for corruption flags "
        "(DISM /Online /Cleanup-Image /CheckHealth).",
        ["DISM", "/Online", "/Cleanup-Image", "/CheckHealth"],
        Category.OS_REPAIR, Risk.READ_ONLY, True, "<1 min",
    ),
    Task(
        "dism_scan", "DISM — Deep health scan",
        "Thorough scan of the component store for corruption "
        "(DISM /Online /Cleanup-Image /ScanHealth).",
        ["DISM", "/Online", "/Cleanup-Image", "/ScanHealth"],
        Category.OS_REPAIR, Risk.READ_ONLY, True, "5-10 min",
    ),
    Task(
        "chkdsk", "CHKDSK — Scan system drive",
        "Read-only scan of the C: drive for file-system errors (chkdsk C:). "
        "Does not lock or modify the drive.",
        ["chkdsk", "C:"],
        Category.OS_REPAIR, Risk.READ_ONLY, True, "2-10 min",
    ),
    Task(
        "dism_cleanup", "DISM — Clean component store",
        "Reclaims disk space by removing superseded components "
        "(DISM /Online /Cleanup-Image /StartComponentCleanup).",
        ["DISM", "/Online", "/Cleanup-Image", "/StartComponentCleanup"],
        Category.OS_REPAIR, Risk.REPAIR, True, "5-20 min",
    ),

    # ------------------------- Network & Runtime -----------------------
    Task(
        "flushdns", "Flush DNS cache",
        "Clears the DNS resolver cache (ipconfig /flushdns). Fixes 'page won't "
        "load' and stale-address problems.",
        ["ipconfig", "/flushdns"],
        Category.NETWORK, Risk.REPAIR, False, "<1 min",
    ),
    Task(
        "winsock", "Reset Winsock catalog",
        "Resets the Windows Sockets catalog (netsh winsock reset). Fixes many "
        "'connected but no internet' issues. Reboot afterwards.",
        ["netsh", "winsock", "reset"],
        Category.NETWORK, Risk.REBOOT, True, "<1 min",
    ),
    Task(
        "tcpip", "Reset TCP/IP stack",
        "Restores TCP/IP settings to defaults (netsh int ip reset). "
        "Reboot afterwards.",
        ["netsh", "int", "ip", "reset"],
        Category.NETWORK, Risk.REBOOT, True, "<1 min",
    ),
    Task(
        "renew", "Renew IP address",
        "Requests a fresh DHCP lease (ipconfig /renew).",
        ["ipconfig", "/renew"],
        Category.NETWORK, Risk.REPAIR, False, "<1 min",
    ),
    Task(
        "ipconfig", "Show network configuration",
        "Displays full network adapter configuration (ipconfig /all). Read-only.",
        ["ipconfig", "/all"],
        Category.NETWORK, Risk.READ_ONLY, False, "<1 min",
    ),
    Task(
        "systeminfo", "Show system information",
        "Dumps OS, BIOS, memory and installed-patch info (systeminfo). Read-only.",
        ["systeminfo"],
        Category.NETWORK, Risk.READ_ONLY, False, "<1 min",
    ),
]


def tasks_for(category: Category) -> list[Task]:
    """All tasks belonging to *category*, in catalog order."""
    return [t for t in TASKS if t.category == category]


def get_task(task_id: str) -> Task | None:
    return next((t for t in TASKS if t.id == task_id), None)
