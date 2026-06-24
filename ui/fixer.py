"""Fix My PC — the guided view.

The user describes the problem in plain words (or picks a common one); the app
classifies it into a remediation :class:`~core.plans.Plan`, shows exactly what it
will do, and — on one click — runs the whole ordered sequence safely, streaming
output to the shared console.
"""
from __future__ import annotations

import asyncio

import flet as ft

from core.executor import execute
from core.plans import PLANS, Plan, classify, get_plan, plan_tasks
from core.state import AppState
from core.tasks import Risk, get_task
from ui.header import AppHeader
from ui.logger import StatusConsole

_RISK_COLOR = {
    Risk.READ_ONLY: ft.Colors.GREEN_400,
    Risk.REPAIR: ft.Colors.AMBER_400,
    Risk.REBOOT: ft.Colors.RED_400,
}
_RISK_LABEL = {
    Risk.READ_ONLY: "safe",
    Risk.REPAIR: "modifies",
    Risk.REBOOT: "reboot after",
}


class Fixer:
    def __init__(self, page: ft.Page, state: AppState,
                 console: StatusConsole, header: AppHeader):
        self.page = page
        self.state = state
        self.console = console
        self.header = header
        self.current_plan: Plan | None = None

        self.problem_input = ft.TextField(
            label="Describe the problem in your own words",
            hint_text="e.g. “Windows won't finish updating and I'm stuck on an old version”",
            multiline=True,
            min_lines=2,
            max_lines=4,
            on_submit=lambda _e: self._build_from_text(),
        )
        self.build_btn = ft.FilledButton(
            "Build my fix plan",
            icon=ft.Icons.AUTO_FIX_HIGH,
            on_click=lambda _e: self._build_from_text(),
        )

        # One quick-pick button per common problem (skip the generic default).
        self.quick_picks = [
            ft.OutlinedButton(
                p.title.split(" / ")[0],
                on_click=lambda _e, plan=p: self._show_plan(plan),
            )
            for p in PLANS if p.id != "general"
        ]
        self.general_btn = ft.TextButton(
            "Not sure? Run a general health check",
            icon=ft.Icons.HEALTH_AND_SAFETY,
            on_click=lambda _e: self._show_plan(get_plan("general")),
        )

        self.plan_box = ft.Column(
            [self._placeholder()], spacing=10, scroll=ft.ScrollMode.AUTO,
        )
        self.run_btn = ft.FilledButton(
            "Run the full fix",
            icon=ft.Icons.PLAY_CIRCLE,
            disabled=True,
            on_click=lambda _e: self.page.run_task(self._run_plan),
            style=ft.ButtonStyle(padding=ft.padding.symmetric(horizontal=22, vertical=16)),
        )

        self.view = ft.Column(
            [
                ft.Row(
                    [ft.Icon(ft.Icons.AUTO_FIX_HIGH, color=ft.Colors.BLUE_300),
                     ft.Text("Fix My PC", size=22, weight=ft.FontWeight.BOLD)],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text(
                    "Tell me what's wrong and I'll do everything needed to fix it "
                    "— in the right order, starting with a safety restore point. "
                    "Nothing runs until you press Run, and Safe Mode lets you "
                    "preview every command first.",
                    size=13, color=ft.Colors.WHITE70,
                ),
                self.problem_input,
                ft.Row([self.build_btn]),
                ft.Container(height=2),
                ft.Text("Or pick a common problem:", size=13, color=ft.Colors.WHITE60),
                ft.Row(self.quick_picks, wrap=True, spacing=8, run_spacing=8),
                ft.Row([self.general_btn]),
                ft.Divider(height=1),
                ft.Container(
                    content=self.plan_box,
                    padding=16,
                    border_radius=10,
                    bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.WHITE),
                    border=ft.border.all(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE)),
                ),
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    # ------------------------------------------------------------------ #
    # Plan building / preview                                            #
    # ------------------------------------------------------------------ #
    def _placeholder(self) -> ft.Control:
        return ft.Row(
            [ft.Icon(ft.Icons.CHECKLIST, color=ft.Colors.WHITE38),
             ft.Text("Your fix plan will appear here.", color=ft.Colors.WHITE38)],
            spacing=8,
        )

    def _build_from_text(self) -> None:
        text = (self.problem_input.value or "").strip()
        if not text:
            self.problem_input.error_text = "Type a short description first."
            self.page.update()
            return
        self.problem_input.error_text = None
        self._show_plan(classify(text))

    def _show_plan(self, plan: Plan | None) -> None:
        if plan is None:
            return
        self.current_plan = plan
        tasks = plan_tasks(plan)

        steps: list[ft.Control] = []
        for i, task in enumerate(tasks, start=1):
            steps.append(
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(str(i), size=12, weight=ft.FontWeight.BOLD),
                            width=24, height=24, border_radius=12,
                            bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.BLUE),
                            alignment=ft.alignment.center,
                        ),
                        ft.Text(task.label, size=13, expand=True),
                        ft.Container(
                            content=ft.Text(_RISK_LABEL[task.risk], size=10,
                                            color=_RISK_COLOR[task.risk]),
                            bgcolor=ft.Colors.with_opacity(0.14, _RISK_COLOR[task.risk]),
                            padding=ft.padding.symmetric(horizontal=7, vertical=2),
                            border_radius=10,
                        ),
                        ft.Text(task.est_minutes, size=11, color=ft.Colors.WHITE54),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )

        notes = [
            ft.Row(
                [ft.Icon(ft.Icons.TIPS_AND_UPDATES, size=16, color=ft.Colors.AMBER),
                 ft.Text(note, size=12, color=ft.Colors.AMBER_200, expand=True)],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
            for note in plan.notes
        ]

        controls: list[ft.Control] = [
            ft.Text(plan.title, size=16, weight=ft.FontWeight.BOLD),
            ft.Text(plan.summary, size=13, color=ft.Colors.WHITE70),
            ft.Container(height=4),
            ft.Text(f"What I'll do ({len(tasks)} steps, in order):",
                    size=12, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE60),
            *steps,
            *([ft.Container(height=4), *notes] if notes else []),
            ft.Container(height=6),
            ft.Row([self.run_btn], alignment=ft.MainAxisAlignment.END),
        ]

        # For the update problem, also offer the one-click in-place upgrade —
        # the real fix when a PC is too far behind (e.g. 1903) for WU to recover.
        if plan.id == "update":
            controls.append(self._upgrade_panel())

        self.plan_box.controls = controls
        self.run_btn.disabled = False
        self.page.update()

    def _upgrade_panel(self) -> ft.Control:
        return ft.Container(
            margin=ft.margin.only(top=8),
            padding=14,
            border_radius=10,
            bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.BLUE),
            border=ft.border.all(1, ft.Colors.with_opacity(0.30, ft.Colors.BLUE)),
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.ROCKET_LAUNCH, color=ft.Colors.BLUE_200),
                    ft.Column(
                        [
                            ft.Text("Still stuck after the repair?",
                                    weight=ft.FontWeight.BOLD, size=13),
                            ft.Text("Upgrade in place to Windows 10 22H2 with "
                                    "Microsoft's Update Assistant — keeps your "
                                    "files and apps. Recommended for your version.",
                                    size=12, color=ft.Colors.WHITE70),
                        ],
                        spacing=2, expand=True,
                    ),
                    ft.FilledButton(
                        "Upgrade to 22H2 now",
                        icon=ft.Icons.SYSTEM_UPDATE,
                        on_click=lambda _e: self.page.run_task(self._run_upgrade),
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    # ------------------------------------------------------------------ #
    # Running                                                            #
    # ------------------------------------------------------------------ #
    def _set_enabled(self, enabled: bool) -> None:
        for ctrl in (self.run_btn, self.build_btn, self.general_btn,
                     self.problem_input, *self.quick_picks):
            ctrl.disabled = not enabled
        self.header.lock(not enabled)
        self.page.update()

    async def _confirm(self, message: str, confirm_label: str = "Yes, do it") -> bool:
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()

        def resolve(value: bool):
            self.page.close(dlg)
            if not fut.done():
                fut.set_result(value)

        dlg = ft.AlertDialog(
            modal=True,
            icon=ft.Icon(ft.Icons.WARNING_AMBER, color=ft.Colors.AMBER),
            title=ft.Text("Run for real?"),
            content=ft.Text(message),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _e: resolve(False)),
                ft.FilledButton(confirm_label, on_click=lambda _e: resolve(True)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dlg)
        return await fut

    async def _run_plan(self) -> None:
        plan = self.current_plan
        if plan is None or self.state.busy:
            return
        if not self.state.dry_run:
            msg = (f"Safe Mode is OFF, so this will run {len(plan_tasks(plan))} "
                   "steps for real. A System Restore point is created first so "
                   "you can roll back. Continue?")
            if not await self._confirm(msg, "Yes, fix it"):
                return

        self.state.busy = True
        self._set_enabled(False)
        tasks = plan_tasks(plan)
        mode = "SAFE MODE / simulation" if self.state.dry_run else "LIVE"
        self.console.append(
            f"\n########## Fix My PC: {plan.title} ##########\n"
            f"Running {len(tasks)} steps ({mode})\n"
        )
        try:
            for task in tasks:
                self.console.set_running(True, task.label)
                rc = await execute(task, self.console.append, dry_run=self.state.dry_run)
                verdict = "SUCCESS" if rc == 0 else f"exit code {rc}"
                self.console.append(f">>> {task.label}: {verdict}\n")
            self.console.append("\n########## Fix sequence finished ##########\n")
            if plan.reboot_after:
                self.console.append(
                    "[!] Please REBOOT your PC to complete these repairs.\n"
                )
        finally:
            self.state.busy = False
            self.console.set_running(False)
            self._set_enabled(True)

    async def _run_upgrade(self) -> None:
        """Download + launch Microsoft's Update Assistant (in-place 22H2 upgrade)."""
        if self.state.busy:
            return
        if not self.state.dry_run:
            ok = await self._confirm(
                "This downloads Microsoft's official Update Assistant and starts "
                "an in-place upgrade to Windows 10 22H2. Your files and apps are "
                "kept, but it takes 30–90 minutes and reboots a few times. "
                "Make sure the PC is plugged in. Continue?",
                confirm_label="Download & upgrade",
            )
            if not ok:
                return

        self.state.busy = True
        self._set_enabled(False)
        self.console.set_running(True, "Windows 10 Update Assistant")
        try:
            task = get_task("wu_upgrade")
            rc = await execute(task, self.console.append, dry_run=self.state.dry_run)
            if rc == 0 and not self.state.dry_run:
                self.console.append(
                    ">>> Update Assistant launched — follow its prompts.\n"
                )
        finally:
            self.state.busy = False
            self.console.set_running(False)
            self._set_enabled(True)
