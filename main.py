"""WHome Diagnostic Tool — application entry point.

A lightweight, asynchronous Windows repair utility built with Flet.

    Run:    python main.py          (or double-click run.bat on Windows)
    Build:  double-click build.bat   ->  standalone dist\\WHomeDiagnostics.exe
            (see README.md for the exact `flet pack` command)

Architecture
------------
    main.py        entry point + Flet page setup + privilege guard + view swap
    core/          business logic (no UI imports)
        admin.py       IsUserAnAdmin() check + UAC self-elevation
        executor.py    asyncio.create_subprocess_exec with live stream piping
        tasks.py       data-only catalog of repair tools
        plans.py       symptom -> ordered remediation plan (+ free-text classify)
        state.py       shared state incl. the global dry_run flag
    ui/            Flet controls (import core, never the reverse)
        sidebar.py     NavigationRail (Fix My PC / Updates / OS Repair / Network)
        fixer.py       guided "describe it, I'll fix it" view
        dashboard.py   task cards + Run buttons
        header.py      global Safe-Mode switch + admin chip + banner
        logger.py      read-only streaming TextField console
        dialogs.py     admin / privilege modals
"""
from __future__ import annotations

import flet as ft

from core.admin import is_admin, is_windows
from core.state import AppState
from core.tasks import Category
from ui.dashboard import Dashboard
from ui.dialogs import show_admin_warning, show_not_windows_warning
from ui.fixer import Fixer
from ui.header import AppHeader
from ui.logger import StatusConsole
from ui.sidebar import build_sidebar

APP_TITLE = "WHome Diagnostic Tool"

# NavigationRail index -> dashboard category (index 0 is the Fixer view).
_CATEGORY_BY_NAV = {
    1: Category.WINDOWS_UPDATE,
    2: Category.OS_REPAIR,
    3: Category.NETWORK,
}


async def main(page: ft.Page) -> None:
    page.title = APP_TITLE
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE)
    page.padding = 0

    try:
        page.window.width = 1200
        page.window.height = 780
        page.window.min_width = 900
        page.window.min_height = 600
        # Make sure the window can be moved, resized and maximized.
        page.window.resizable = True
        page.window.maximizable = True
        page.window.minimizable = True
        page.window.movable = True
        page.window.center()
    except Exception:
        pass

    state = AppState(dry_run=True, is_admin=is_admin())

    # Build the UI tree. The header owns the global Safe Mode switch + banner.
    console = StatusConsole(page)
    header = AppHeader(page, state, notify=console.append)
    dashboard = Dashboard(page, state, console, header)
    fixer = Fixer(page, state, console, header)

    # The centre panel swaps between the guided Fixer and the category dashboard.
    content = ft.Container(fixer.view, expand=5, padding=ft.padding.only(left=16, top=4))

    def on_nav_change(e: ft.ControlEvent) -> None:
        index = e.control.selected_index
        if index == 0:
            content.content = fixer.view
        else:
            dashboard.show_category(_CATEGORY_BY_NAV[index])
            content.content = dashboard.view
        page.update()

    rail = build_sidebar(on_nav_change)

    page.add(
        ft.Column(
            [
                ft.Container(header.bar,
                             padding=ft.padding.only(left=16, right=16, top=12)),
                ft.Container(header.safe_banner,
                             padding=ft.padding.symmetric(horizontal=16)),
                ft.Row(
                    [
                        rail,
                        ft.VerticalDivider(width=1),
                        content,
                        ft.Container(
                            console.view, expand=4,
                            padding=ft.padding.only(right=16, top=4, bottom=16, left=8),
                        ),
                    ],
                    expand=True, spacing=0,
                    vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
            ],
            expand=True, spacing=10,
        )
    )

    # ----------------------------------------------------------------- #
    # Privilege guard — runs immediately on startup.                    #
    # ----------------------------------------------------------------- #
    if not is_windows():
        # Force safe mode and lock the toggle: there is nothing real to run.
        state.dry_run = True
        header.safe_switch.value = True
        header.safe_switch.disabled = True
        header.refresh()
        page.update()
        show_not_windows_warning(page)
    elif not state.is_admin:
        show_admin_warning(page)


if __name__ == "__main__":
    # Desktop window. Flet uses the Proactor event loop on Windows, which
    # supports asyncio subprocesses out of the box.
    ft.app(target=main)
