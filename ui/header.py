"""Global application header.

Owns the controls that must be consistent across every view: the Administrator
status chip and — importantly — the single **Safe Mode** switch plus the
coloured safe/live banner. Keeping these in one place means the same Safe Mode
toggle governs the Fixer, the Updates tab and every category, with no two-switch
sync problems.
"""
from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from core.state import AppState


class AppHeader:
    def __init__(self, page: ft.Page, state: AppState,
                 notify: Optional[Callable[[str], None]] = None):
        self.page = page
        self.state = state
        self._notify = notify

        self.admin_chip = ft.Container(
            border_radius=20, padding=ft.padding.symmetric(horizontal=12, vertical=6),
        )
        self.safe_switch = ft.Switch(
            value=state.dry_run, active_color=ft.Colors.GREEN, on_change=self._toggle,
        )
        self.safe_banner = ft.Container(border_radius=8, padding=12)

        self.bar = ft.Row(
            [
                ft.Icon(ft.Icons.MEDICAL_SERVICES, color=ft.Colors.BLUE_300),
                ft.Text("WHome Diagnostic Tool", size=20, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                self.admin_chip,
                ft.Container(width=14),
                ft.Icon(ft.Icons.SHIELD_OUTLINED, size=18),
                ft.Text("Safe Mode", size=13),
                self.safe_switch,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.refresh()

    # ------------------------------------------------------------------ #
    def _toggle(self, _e) -> None:
        self.state.dry_run = self.safe_switch.value
        self.refresh()
        if self._notify:
            self._notify(
                f"\n[Safe Mode {'ON — simulating commands' if self.state.dry_run else 'OFF — REAL commands will run'}]\n"
            )
        self.page.update()

    def lock(self, locked: bool) -> None:
        """Disable the Safe Mode switch while a task is running."""
        self.safe_switch.disabled = locked
        self.page.update()

    def refresh(self) -> None:
        # Administrator status chip.
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

        # Safe / live banner.
        if self.state.dry_run:
            self.safe_banner.bgcolor = ft.Colors.with_opacity(0.12, ft.Colors.GREEN)
            self.safe_banner.content = ft.Row(
                [ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN),
                 ft.Text("SAFE MODE (Dry Run) is ON — commands are simulated, "
                         "nothing on your PC changes. Toggle it off to perform "
                         "real repairs.", expand=True)],
                spacing=10,
            )
        else:
            self.safe_banner.bgcolor = ft.Colors.with_opacity(0.16, ft.Colors.RED)
            self.safe_banner.content = ft.Row(
                [ft.Icon(ft.Icons.WARNING_AMBER, color=ft.Colors.RED_300),
                 ft.Text("LIVE MODE — Safe Mode is OFF. Commands run for real and "
                         "can change your system. A restore point is made first.",
                         expand=True, weight=ft.FontWeight.BOLD)],
                spacing=10,
            )
