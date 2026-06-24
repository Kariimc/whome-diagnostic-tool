"""Dashboard — renders task cards for the selected category and wires each
"Run" button to the asynchronous executor.

The dashboard owns no business logic: it reads the task catalog from
``core.tasks`` and delegates execution to ``core.executor.execute`` (which
dispatches single-command and multi-step tasks alike), passing the live
``dry_run`` flag and the console's ``append`` as the output sink. The Safe Mode
switch and admin chip live in the shared :class:`~ui.header.AppHeader`.
"""
from __future__ import annotations

import flet as ft

from core.executor import execute
from core.state import AppState
from core.tasks import Category, Risk, Task, tasks_for
from ui.header import AppHeader
from ui.logger import StatusConsole

_SECTION_TITLE = {
    Category.WINDOWS_UPDATE: "Windows Update Repair",
    Category.OS_REPAIR: "Windows OS Repair",
    Category.NETWORK: "Network & Runtime",
}
_SECTION_SUB = {
    Category.WINDOWS_UPDATE:
        "Fix updates that won't download or never finish installing. "
        "Tip: use “Run all in this section” for the full repair sequence.",
    Category.OS_REPAIR:
        "Repair corrupted system files and the Windows image.",
    Category.NETWORK:
        "Fix connectivity problems and inspect the system.",
}
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
    def __init__(self, page: ft.Page, state: AppState,
                 console: StatusConsole, header: AppHeader):
        self.page = page
        self.state = state
        self.console = console
        self.header = header
        self.category = Category.WINDOWS_UPDATE
        self._run_buttons: list[ft.Control] = []

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
    def show_category(self, category: Category) -> None:
        self.category = category
        self.render()

    def render(self) -> None:
        self._run_buttons = []
        self.section_title.value = _SECTION_TITLE[self.category]
        self.section_sub.value = _SECTION_SUB[self.category]
        self.cards.controls = [self._task_card(t) for t in tasks_for(self.category)]
        if self.state.busy:
            self._set_buttons_enabled(False)
        self.page.update()

    def _set_buttons_enabled(self, enabled: bool) -> None:
        for btn in self._run_buttons:
            btn.disabled = not enabled
        self.run_all_btn.disabled = not enabled
        self.header.lock(not enabled)
        self.page.update()

    # ------------------------------------------------------------------ #
    # Event handlers                                                     #
    # ------------------------------------------------------------------ #
    async def _run(self, task: Task) -> None:
        if self.state.busy:
            return
        self.state.busy = True
        self._set_buttons_enabled(False)
        self.console.set_running(True, task.label)
        try:
            rc = await execute(task, self.console.append, dry_run=self.state.dry_run)
            verdict = "SUCCESS" if rc == 0 else f"finished with exit code {rc}"
            self.console.append(f">>> {task.label}: {verdict}\n")
        finally:
            self.state.busy = False
            self.console.set_running(False)
            self._set_buttons_enabled(True)

    async def _run_all(self) -> None:
        if self.state.busy:
            return
        self.state.busy = True
        self._set_buttons_enabled(False)
        # Skip interactive actions (e.g. launching the Update Assistant) — those
        # are run deliberately from their own button, not as part of a sweep.
        section = [t for t in tasks_for(self.category) if not t.action]
        self.console.append(
            f"\n========== Running all {len(section)} tools in "
            f"'{self.category.value}' ==========\n"
        )
        try:
            for task in section:
                self.console.set_running(True, task.label)
                rc = await execute(task, self.console.append, dry_run=self.state.dry_run)
                verdict = "SUCCESS" if rc == 0 else f"exit code {rc}"
                self.console.append(f">>> {task.label}: {verdict}\n")
            self.console.append("\n========== All tools finished ==========\n")
        finally:
            self.state.busy = False
            self.console.set_running(False)
            self._set_buttons_enabled(True)
