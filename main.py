"""WHome Diagnostic Tool — application entry point.

A lightweight, asynchronous Windows repair utility built with Flet.

    Run:    python main.py          (or double-click run.bat on Windows)
    Build:  double-click build.bat   ->  standalone dist\\WHomeDiagnostics.exe
            (see README.md for the exact `flet pack` command)

Architecture
------------
    main.py        entry point + Flet page setup + privilege guard
    core/          business logic (no UI imports)
        admin.py       IsUserAnAdmin() check + UAC self-elevation
        executor.py    asyncio.create_subprocess_exec with live stream piping
        tasks.py       data-only catalog of repair tools
        state.py       shared state incl. the global dry_run flag
    ui/            Flet controls (import core, never the reverse)
        sidebar.py     NavigationRail (OS Repair vs Network)
        dashboard.py   task cards + Run buttons + safe-mode toggle
        logger.py      read-only streaming TextField console
        dialogs.py     admin / privilege modals
"""
from __future__ import annotations

import flet as ft

from core.admin import is_admin, is_windows
from core.state import AppState
from ui.dashboard import Dashboard
from ui.dialogs import show_admin_warning, show_not_windows_warning
from ui.logger import StatusConsole
from ui.sidebar import build_sidebar

APP_TITLE = "WHome Diagnostic Tool"


async def main(page: ft.Page) -> None:
    page.title = APP_TITLE
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE)
    page.padding = 0

    # Window sizing (guarded — harmless if running in the browser).
    try:
        page.window.width = 1180
        page.window.height = 760
        page.window.min_width = 940
        page.window.min_height = 600
        page.window.center()
    except Exception:
        pass

    state = AppState(dry_run=True, is_admin=is_admin())

    # Build the UI tree.
    console = StatusConsole(page)
    dashboard = Dashboard(page, state, console)

    def on_nav_change(e: ft.ControlEvent) -> None:
        dashboard.select_index(e.control.selected_index)

    rail = build_sidebar(on_nav_change)

    page.add(
        ft.Row(
            [
                rail,
                ft.VerticalDivider(width=1),
                ft.Container(dashboard.view, expand=5, padding=16),
                ft.Container(
                    console.view,
                    expand=4,
                    padding=ft.padding.only(right=16, top=16, bottom=16),
                ),
            ],
            expand=True,
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        )
    )

    # ----------------------------------------------------------------- #
    # Privilege guard — runs immediately on startup.                    #
    # ----------------------------------------------------------------- #
    if not is_windows():
        # Force safe mode and lock the toggle: there is nothing real to run.
        state.dry_run = True
        dashboard.dry_switch.value = True
        dashboard.dry_switch.disabled = True
        dashboard.render()
        show_not_windows_warning(page)
    elif not state.is_admin:
        show_admin_warning(page)


if __name__ == "__main__":
    # Desktop window. Flet uses the Proactor event loop on Windows, which
    # supports asyncio subprocesses out of the box.
    ft.app(target=main)
