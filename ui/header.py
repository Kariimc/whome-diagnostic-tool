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
                ft.Container(width=12),
                ft.IconButton(ft.Icons.REMOVE, tooltip="Minimize", icon_size=20,
                              on_click=self._minimize),
                ft.IconButton(ft.Icons.CROP_SQUARE, tooltip="Maximize / restore",
                              icon_size=18, on_click=self._toggle_max),
                ft.IconButton(ft.Icons.CLOSE, tooltip="Exit", icon_size=20,
                              icon_color=ft.Colors.RED_300, on_click=self._exit),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.refresh()

    # ------------------------------------------------------------------ #
    # Window controls                                                    #
    # ------------------------------------------------------------------ #
    def _minimize(self, _e) -> None:
        try:
            self.page.window.minimized = True
            self.page.update()
        except Exception:
            pass

    def _toggle_max(self, _e) -> None:
        try:
            self.page.window.maximized = not self.page.window.maximized
            self.page.update()
        except Exception:
            pass

    def _exit(self, _e) -> None:
        # If a repair is running, confirm before killing it mid-flight.
        if self.state.busy:
            dlg = ft.AlertDialog(
                modal=True,
                icon=ft.Icon(ft.Icons.WARNING_AMBER, color=ft.Colors.AMBER),
                title=ft.Text("A repair is still running"),
                content=ft.Text("Exiting now stops it partway, which could leave a "
                                "repair incomplete. Exit anyway?"),
                actions=[
                    ft.TextButton("Stay", on_click=lambda _e: self.page.close(dlg)),
                    ft.FilledButton("Exit anyway",
                                    on_click=lambda _e: (self.page.close(dlg), self._do_exit())),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            self.page.open(dlg)
        else:
            self._do_exit()

    def _do_exit(self) -> None:
        try:
            self.page.window.close()
        except Exception:
            try:
                self.page.window.destroy()
            except Exception:
                pass

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
