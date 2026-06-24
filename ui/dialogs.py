"""Modal dialogs: the privilege guard and a Windows-only notice."""
from __future__ import annotations

import flet as ft

from core.admin import relaunch_as_admin


def show_admin_warning(page: ft.Page, on_continue=None) -> None:
    """Immediate startup modal when the app is *not* running elevated.

    Offers to relaunch elevated (UAC ``runas``) or to continue with limited,
    read-only capability.
    """

    def _elevate(_e) -> None:
        if relaunch_as_admin():
            # The elevated instance is launching; close this un-elevated one.
            try:
                page.window.destroy()
            except Exception:
                page.close(dlg)
        else:
            page.close(dlg)
            page.open(
                ft.SnackBar(
                    ft.Text("Could not elevate. Right-click the app and choose "
                            "“Run as administrator”.")
                )
            )

    def _continue(_e) -> None:
        page.close(dlg)
        if on_continue:
            on_continue()

    dlg = ft.AlertDialog(
        modal=True,
        icon=ft.Icon(ft.Icons.SHIELD_OUTLINED, color=ft.Colors.AMBER),
        title=ft.Text("Administrator rights recommended"),
        content=ft.Text(
            "Most repair tools — SFC, DISM, CHKDSK and the network resets — "
            "require Administrator privileges to make changes.\n\n"
            "You can restart the app elevated now, or continue with limited "
            "(read-only) capability.",
        ),
        actions=[
            ft.TextButton("Continue anyway", on_click=_continue),
            ft.FilledButton(
                "Restart as Administrator",
                icon=ft.Icons.SHIELD,
                on_click=_elevate,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.open(dlg)


def show_not_windows_warning(page: ft.Page) -> None:
    """Shown when the app runs on a non-Windows OS (preview / safe mode)."""
    dlg = ft.AlertDialog(
        modal=True,
        icon=ft.Icon(ft.Icons.INFO_OUTLINE, color=ft.Colors.BLUE),
        title=ft.Text("Preview mode"),
        content=ft.Text(
            "This is a Windows repair utility, but it isn’t running on Windows.\n\n"
            "The interface is fully usable for preview, and Safe Mode (Dry Run) "
            "is forced ON so no commands will be executed.",
        ),
        actions=[ft.FilledButton("Got it", on_click=lambda _e: page.close(dlg))],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.open(dlg)
