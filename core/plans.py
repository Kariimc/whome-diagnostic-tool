"""Guided remediation plans.

A *plan* maps a real-world problem ("Windows won't update", "no internet") to an
ordered, safe sequence of catalog tasks. The :func:`classify` function turns a
free-text description from the user into the best-matching plan using simple,
fully-offline keyword scoring — so the user can "tell the app what's wrong" and
get the right fix without needing to know which tool to run.

Plans deliberately start with the least invasive steps and (where it matters)
create a System Restore point first, so running one is safe by design.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.tasks import Task, get_task


@dataclass(frozen=True)
class Plan:
    id: str
    title: str
    summary: str
    task_ids: list[str]
    keywords: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    reboot_after: bool = False


# Ordered roughly most-common-first. The last entry ("general") is the default
# when nothing else matches.
PLANS: list[Plan] = [
    Plan(
        "update",
        "Windows Update won't finish / PC is behind on updates",
        "Creates a restore point, clears the broken Windows Update download "
        "cache, repairs the Windows image and system files, then re-checks for "
        "updates.",
        task_ids=[
            "restore_point", "wu_reset", "wu_dism", "wu_sfc", "wu_rescan",
            "open_win10_download",
        ],
        keywords=[
            "update", "updates", "updating", "wont update", "won't update",
            "cant update", "can't update", "behind", "upgrade", "1903", "1909",
            "feature update", "stuck", "downloading", "0x80", "windows update",
            "never finish", "never completes", "checking for updates",
        ],
        notes=[
            "Your PC is on Windows 10 version 1903, which is past Microsoft's "
            "end-of-support — so Windows Update may not be able to jump all the "
            "way to the current version on its own.",
            "After these repairs, if updates still won't appear, use the "
            "Windows 10 Update Assistant from the Microsoft page this plan "
            "opens to upgrade in place to 22H2. It keeps your files and apps.",
            "Reboot once the plan finishes.",
        ],
        reboot_after=True,
    ),
    Plan(
        "network",
        "No internet / Wi-Fi or network problems",
        "Flushes DNS and resets the Winsock and TCP/IP networking stack.",
        task_ids=["flushdns", "winsock", "tcpip", "renew"],
        keywords=[
            "internet", "wifi", "wi-fi", "network", "connect", "connection",
            "dns", "no internet", "offline", "ethernet", "router", "browsing",
            "cant connect", "can't connect", "limited connectivity",
        ],
        notes=["Reboot afterwards — the Winsock and TCP/IP resets need a "
               "restart to fully take effect."],
        reboot_after=True,
    ),
    Plan(
        "performance",
        "PC is slow, freezing, or laggy",
        "Creates a restore point, repairs system files, checks the disk, and "
        "frees space used by old Windows components.",
        task_ids=["restore_point", "dism_restore", "sfc_scan", "chkdsk",
                  "dism_cleanup"],
        keywords=[
            "slow", "freez", "lag", "hang", "stutter", "sluggish",
            "performance", "100% disk", "unresponsive", "slow boot",
        ],
        notes=["A reboot is recommended after this plan."],
        reboot_after=True,
    ),
    Plan(
        "crashes",
        "Crashes, blue screens (BSOD), or corrupted system files",
        "Creates a restore point, repairs the Windows image and system files, "
        "then scans the disk for errors.",
        task_ids=["restore_point", "dism_restore", "sfc_scan", "chkdsk"],
        keywords=[
            "crash", "crashing", "bsod", "blue screen", "corrupt", "missing dll",
            "wont boot", "won't boot", "stop code", "reboot loop", "error",
            "freezes and restarts",
        ],
        notes=["If the PC can't stay on long enough to finish, run this from "
               "Windows Safe Mode."],
        reboot_after=True,
    ),
    Plan(
        "disk",
        "Running out of disk space",
        "Reclaims disk space by removing superseded Windows components.",
        task_ids=["dism_cleanup"],
        keywords=["space", "full", "disk full", "storage", "no space",
                  "low disk", "running out"],
        notes=["For more space, also run the built-in Disk Cleanup (cleanmgr) "
               "to clear temporary files."],
    ),
    Plan(
        "general",
        "General health check (not sure what's wrong)",
        "A safe, thorough diagnosis and repair: restore point, then verify and "
        "repair the Windows image and system files.",
        task_ids=["restore_point", "sfc_verify", "dism_check", "dism_restore",
                  "sfc_scan"],
        keywords=[],  # default fallback
        notes=["This is a safe default that finds and fixes the most common "
               "Windows problems."],
    ),
]

_PLAN_BY_ID = {p.id: p for p in PLANS}
DEFAULT_PLAN_ID = "general"


def get_plan(plan_id: str) -> Plan | None:
    return _PLAN_BY_ID.get(plan_id)


def plan_tasks(plan: Plan) -> list[Task]:
    """Resolve a plan's task ids to Task objects (skipping any unknown id)."""
    resolved = [get_task(tid) for tid in plan.task_ids]
    return [t for t in resolved if t is not None]


def classify(text: str) -> Plan:
    """Pick the best-matching plan for a free-text problem description.

    Scores each plan by how many of its keywords appear in *text*; longer
    keyword phrases are weighted more so "won't update" beats a stray "update".
    Falls back to the general health-check plan when nothing matches.
    """
    haystack = (text or "").lower()
    best: Plan | None = None
    best_score = 0
    for plan in PLANS:
        score = 0
        for kw in plan.keywords:
            if kw in haystack:
                # Weight multi-word phrases higher than single words.
                score += 2 if " " in kw else 1
        if score > best_score:
            best_score, best = score, plan
    return best or _PLAN_BY_ID[DEFAULT_PLAN_ID]
