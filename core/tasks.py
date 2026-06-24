"""Catalog of diagnostic / repair tasks.

Each :class:`Task` is a *pure data* description — no UI and no execution logic —
so it can be rendered by the dashboard and run by the executor independently.
The commands here are the genuinely useful Windows repair tools.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Category(str, Enum):
    WINDOWS_UPDATE = "Windows Update"
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
    command: list[str] = field(default_factory=list)
    category: Category = Category.OS_REPAIR
    risk: Risk = Risk.READ_ONLY
    requires_admin: bool = True
    est_minutes: str = "1-3 min"
    # When set, the task runs these commands in sequence instead of `command`
    # (used by the multi-step Windows Update reset). Takes precedence.
    steps: list[list[str]] | None = None
    # When set, the task runs a named Python action (see core.upgrade.ACTIONS)
    # instead of a command — e.g. download-and-launch the Update Assistant.
    # Highest precedence. Action tasks are interactive, so "Run all" skips them.
    action: str | None = None

    @property
    def command_str(self) -> str:
        return " ".join(self.command)

    @property
    def is_multistep(self) -> bool:
        return bool(self.steps)


# Ordered roughly by "try this first". Commands are passed to
# create_subprocess_exec as argument lists (no shell), so each token is literal.
TASKS: list[Task] = [
    # ------------------------- Windows Update --------------------------
    # Ordered so "Run all in this section" performs the full, canonical
    # stuck-update repair: clear cache -> repair image -> repair files -> rescan.
    Task(
        "wu_reset", "Reset Windows Update (fix stuck updates)",
        "The #1 fix for updates that download forever or never install. Stops "
        "the update services, clears the corrupted SoftwareDistribution and "
        "catroot2 download caches (renamed to .old as a safe backup), then "
        "restarts the services so Windows downloads them fresh.",
        category=Category.WINDOWS_UPDATE, risk=Risk.REPAIR,
        requires_admin=True, est_minutes="1-2 min",
        steps=[
            ["net", "stop", "wuauserv"],
            ["net", "stop", "bits"],
            ["net", "stop", "cryptsvc"],
            ["net", "stop", "msiserver"],
            ["cmd", "/c", "rd", "/s", "/q", r"%SystemRoot%\SoftwareDistribution.old"],
            ["cmd", "/c", "rd", "/s", "/q", r"%SystemRoot%\System32\catroot2.old"],
            ["cmd", "/c", "ren", r"%SystemRoot%\SoftwareDistribution", "SoftwareDistribution.old"],
            ["cmd", "/c", "ren", r"%SystemRoot%\System32\catroot2", "catroot2.old"],
            ["net", "start", "wuauserv"],
            ["net", "start", "bits"],
            ["net", "start", "cryptsvc"],
            ["net", "start", "msiserver"],
        ],
    ),
    Task(
        "wu_dism", "Repair Windows image (DISM)",
        "Repairs the component store that Windows Update installs into. A "
        "corrupt store is a common reason updates fail with errors such as "
        "0x80073712 (DISM /Online /Cleanup-Image /RestoreHealth).",
        ["DISM", "/Online", "/Cleanup-Image", "/RestoreHealth"],
        Category.WINDOWS_UPDATE, Risk.REPAIR, True, "10-30 min",
    ),
    Task(
        "wu_sfc", "Repair system files (SFC)",
        "Repairs protected system files the update process depends on "
        "(sfc /scannow).",
        ["sfc", "/scannow"],
        Category.WINDOWS_UPDATE, Risk.REPAIR, True, "5-15 min",
    ),
    Task(
        "wu_rescan", "Re-check for updates now",
        "Triggers Windows to scan for updates again (UsoClient StartScan) after "
        "the repairs. The scan runs in the background — reopen "
        "Settings ▸ Windows Update to watch it install.",
        ["UsoClient", "StartScan"],
        Category.WINDOWS_UPDATE, Risk.REPAIR, True, "<1 min",
    ),
    Task(
        "wu_bounce", "Restart Update services only",
        "A lighter step that simply stops and restarts the Windows Update and "
        "BITS services without clearing the cache. Try this first for a hung "
        "'Checking for updates'.",
        category=Category.WINDOWS_UPDATE, risk=Risk.REPAIR,
        requires_admin=True, est_minutes="<1 min",
        steps=[
            ["net", "stop", "wuauserv"],
            ["net", "stop", "bits"],
            ["net", "start", "wuauserv"],
            ["net", "start", "bits"],
        ],
    ),
    Task(
        "wu_upgrade", "⬆ Upgrade to Windows 10 22H2 now",
        "Downloads Microsoft's official Update Assistant and launches it to "
        "upgrade this PC in place to the latest version (22H2), keeping your "
        "files and apps. This is the real fix when you're too far behind for "
        "Windows Update to catch up on its own (e.g. stuck on 1903). Takes "
        "30–90 minutes with a few automatic reboots.",
        category=Category.WINDOWS_UPDATE, risk=Risk.REBOOT,
        requires_admin=True, est_minutes="30-90 min",
        action="upgrade_assistant",
    ),
    Task(
        "open_win10_download", "Open the Windows 10 upgrade page",
        "Opens Microsoft's official download page in your browser. If your PC is "
        "too far behind for Windows Update to catch up on its own, download the "
        "Update Assistant there to upgrade in place to the latest version — it "
        "keeps your files and apps.",
        ["cmd", "/c", "start", "", "https://www.microsoft.com/software-download/windows10"],
        Category.WINDOWS_UPDATE, Risk.READ_ONLY, False, "<1 min",
    ),

    # ---------------------------- OS Repair ----------------------------
    Task(
        "restore_point", "Create a safety restore point",
        "Turns on System Protection and snapshots the system so you can roll "
        "back if anything goes wrong. A safe first step before bigger repairs. "
        "(Windows may skip it if one was already made in the last 24 hours.)",
        category=Category.OS_REPAIR, risk=Risk.READ_ONLY,
        requires_admin=True, est_minutes="<1 min",
        steps=[
            ["powershell", "-NoProfile", "-Command", "Enable-ComputerRestore -Drive 'C:\\'"],
            ["powershell", "-NoProfile", "-Command",
             "Checkpoint-Computer -Description 'WHome Diagnostic Tool' "
             "-RestorePointType 'MODIFY_SETTINGS'"],
        ],
    ),
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
