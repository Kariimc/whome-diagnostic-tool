"""Dashboard — renders task cards for the selected category and wires each
"Run" button to the asynchronous executor.

The dashboard owns no business logic: it reads the task catalog from
``core.tasks`` and delegates execution to ``core.executor.run_command``,
passing the live ``dry_run`` flag and the console's ``append`` as the output
sink.
"""
from __future__ import annotations

import flet as ft

from core.executor import run_command
from core.state import AppState
from core.tasks import Category, Risk, Task, tasks_for
from ui.logger import StatusConsole

# Category order must match the NavigationRail destinations in sidebar.py.
_CATEGORY_BY_INDEX = [Category.OS_REPAIR, Category.NETWORK]

_RISK_COLOR = {
    Risk.READ_ONLY: ft.Colors.GREEN_400,
    Risk.REPAIR: ft.Colors.AMBER_400,
    Risk.REBOOT: ft.Colors.RED_400,
}
_RISK_LABEL = {
    Risk.READ_ONLY: "SAFE • read-only",
    Risk.REPAIR: "MODIFIES SYSTEM",
    Risk.REBOOT: "MODIFIES • reboot after",
}


class Dashboard:
    def __init__(self, page: ft.Page, state: AppState, console: StatusConsole):
        self.page = page
        self.state = state
        self.console = console
        self.category = Category.OS_REPAIR
        self._run_buttons: list[ft.Control] = []

        # Safe-mode (dry-run) switch.
        self.dry_switch = ft.Switch(
            value=state.dry_run,
            on_change=self._toggle_dry,
            active_color=ft.Colors.GREEN,
        )

        # Banner that changes colour with the safe-mode state.
        self.safe_banner = ft.Container(border_radius=8, padding=12)

        # Admin status chip.
        self.admin_chip = ft.Container(
            border_radius=20, padding=ft.padding.symmetric(horizontal=12, vertical=6)
        )

        self.section_title = ft.Text(size=20, weight=ft.FontWeight.BOLD)
        self.section_sub = ft.Text(size=13, color=ft.Colors.WHITE60)

        self.run_all_btn = ft.OutlinedButton(
            "Run all in this section",
            icon=ft.Icons.PLAYLIST_PLAY,
            on_click=lambda _e: self.page.run_task(self._run_all),
        )

        self.cards = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

        self.view = ft.Column(
            [
                self._build_header(),
                self.safe_banner,
                ft.Row(
                    [self.section_title, ft.Container(expand=True), self.run_all_btn],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self.section_sub,
                ft.Divider(height=1),
                self.cards,
            ],
            expand=True,
            spacing=12,
        )

        self.render()

    # ------------------------------------------------------------------ #
    # Header / banners                                                   #
    # ------------------------------------------------------------------ #
    def _build_header(self) -> ft.Control:
        title = ft.Row(
            [
                ft.Icon(ft.Icons.MEDICAL_SERVICES, color=ft.Colors.BLUE_300),
                ft.Text("WHome Diagnostic Tool", size=22, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                self.admin_chip,
                ft.Container(width=16),
                ft.Row(
                    [ft.Icon(ft.Icons.SHIELD_OUTLINED, size=18), ft.Text("Safe Mode"),
                     self.dry_switch],
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        return title

    def _refresh_admin_chip(self) -> None:
        if self.state.is_admin:
            self.admin_chip.bgcolor = ft.Colors.with_opacity(0.18, ft.Colors.GREEN)
            self.admin_chip.content = ft.Row(
                [ft.Icon(ft.Icons.VERIFIED_USER, size=16, color=ft.Colors.GREEN),
                 ft.Text("Administrator", size=12, color=ft.Colors.GREEN_200)],
                spacing=6, tight=True,
            )
        else:
            self.admin_chip.bgcolor = ft.Colors.with_opacity(0.18, ft.Colors.RED)
            self.admin_chip.content = ft.Row(
                [ft.Icon(ft.Icons.GPP_MAYBE, size=16, color=ft.Colors.RED_300),
                 ft.Text("Not elevated", size=12, color=ft.Colors.RED_200)],
                spacing=6, tight=True,
            )

    def _refresh_safe_banner(self) -> None:
        if self.state.dry_run:
            self.safe_banner.bgcolor = ft.Colors.with_opacity(0.12, ft.Colors.GREEN)
            self.safe_banner.content = ft.Row(
                [
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN),
                    ft.Text(
                        "SAFE MODE (Dry Run) is ON — commands are simulated, "
                        "nothing on your PC changes. Toggle it off to perform "
                        "real repairs.",
                        expand=True,
                    ),
                ],
                spacing=10,
            )
        else:
            self.safe_banner.bgcolor = ft.Colors.with_opacity(0.16, ft.Colors.RED)
            self.safe_banner.content = ft.Row(
                [
                    ft.Icon(ft.Icons.WARNING_AMBER, color=ft.Colors.RED_300),
                    ft.Text(
                        "LIVE MODE — Safe Mode is OFF. Commands will run for real "
                        "and can change your system. Proceed with care.",
                        expand=True,
                        weight=ft.FontWeight.BOLD,
                    ),
                ],
                spacing=10,
            )

    # ------------------------------------------------------------------ #
    # Task cards                                                         #
    # ------------------------------------------------------------------ #
    def _task_card(self, task: Task) -> ft.Control:
        run_btn = ft.FilledButton(
            "Run",
            icon=ft.Icons.PLAY_ARROW,
            on_click=lambda _e, t=task: self.page.run_task(self._run, t),
        )
        self._run_buttons.append(run_btn)

        risk_chip = ft.Container(
            content=ft.Text(_RISK_LABEL[task.risk], size=11, weight=ft.FontWeight.BOLD,
                            color=_RISK_COLOR[task.risk]),
            bgcolor=ft.Colors.with_opacity(0.14, _RISK_COLOR[task.risk]),
            padding=ft.padding.symmetric(horizontal=8, vertical=3),
            border_radius=12,
        )
        meta = ft.Row(
            [
                risk_chip,
                ft.Container(width=8),
                ft.Icon(ft.Icons.SCHEDULE, size=13, color=ft.Colors.WHITE54),
                ft.Text(task.est_minutes, size=11, color=ft.Colors.WHITE54),
                ft.Container(width=8),
                ft.Icon(ft.Icons.SHIELD, size=13, color=ft.Colors.WHITE54),
                ft.Text("Admin required" if task.requires_admin else "No admin needed",
                        size=11, color=ft.Colors.WHITE54),
            ],
            spacing=4,
            wrap=True,
        )

        return ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(task.label, size=15, weight=ft.FontWeight.W_600),
                            ft.Text(task.description, size=12.5, color=ft.Colors.WHITE70),
                            ft.Container(height=2),
                            meta,
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    ft.Container(width=12),
                    run_btn,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=14,
            border_radius=10,
            bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.WHITE),
            border=ft.border.all(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE)),
        )

    # ------------------------------------------------------------------ #
    # Rendering / navigation                                            #
    # ------------------------------------------------------------------ #
    def select_index(self, index: int) -> None:
        self.category = _CATEGORY_BY_INDEX[index % len(_CATEGORY_BY_INDEX)]
        self.render()

    def render(self) -> None:
        self._run_buttons = []
        is_os = self.category == Category.OS_REPAIR
        self.section_title.value = (
            "Windows OS Repair" if is_os else "Network & Runtime"
        )
        self.section_sub.value = (
            "Repair corrupted system files and the Windows image."
            if is_os else
            "Fix connectivity problems and inspect the system."
        )
        self.cards.controls = [self._task_card(t) for t in tasks_for(self.category)]
        self._refresh_admin_chip()
        self._refresh_safe_banner()
        # Keep buttons disabled if a task is mid-flight (e.g. during Run all).
        if self.state.busy:
            self._set_buttons_enabled(False)
        self.page.update()

    def _set_buttons_enabled(self, enabled: bool) -> None:
        for btn in self._run_buttons:
            btn.disabled = not enabled
        self.run_all_btn.disabled = not enabled
        self.dry_switch.disabled = not enabled
        self.page.update()

    # ------------------------------------------------------------------ #
    # Event handlers                                                     #
    # ------------------------------------------------------------------ #
    def _toggle_dry(self, _e) -> None:
        self.state.dry_run = self.dry_switch.value
        self._refresh_safe_banner()
        self.console.append(
            f"\n[Safe Mode {'ON — simulating commands' if self.state.dry_run else 'OFF — REAL commands will run'}]\n"
        )
        self.page.update()

    async def _run(self, task: Task) -> None:
        """Execute a single task, streaming output to the console."""
        if self.state.busy:
            return
        self.state.busy = True
        self._set_buttons_enabled(False)
        self.console.set_running(True, task.label)
        try:
            rc = await run_command(
                task.command,
                self.console.append,
                dry_run=self.state.dry_run,
                label=task.label,
            )
            verdict = "SUCCESS" if rc == 0 else f"finished with exit code {rc}"
            self.console.append(f">>> {task.label}: {verdict}\n")
        finally:
            self.state.busy = False
            self.console.set_running(False)
            self._set_buttons_enabled(True)

    async def _run_all(self) -> None:
        """Run every task in the current section, in order."""
        if self.state.busy:
            return
        self.state.busy = True
        self._set_buttons_enabled(False)
        section = tasks_for(self.category)
        self.console.append(
            f"\n========== Running all {len(section)} tools in "
            f"'{self.category.value}' ==========\n"
        )
        try:
            for task in section:
                self.console.set_running(True, task.label)
                rc = await run_command(
                    task.command,
                    self.console.append,
                    dry_run=self.state.dry_run,
                    label=task.label,
                )
                verdict = "SUCCESS" if rc == 0 else f"exit code {rc}"
                self.console.append(f">>> {task.label}: {verdict}\n")
            self.console.append("\n========== All tools finished ==========\n")
        finally:
            self.state.busy = False
            self.console.set_running(False)
            self._set_buttons_enabled(True)
