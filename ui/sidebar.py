"""Left navigation rail.

Index 0 -> Fix My PC (guided), 1 -> Updates, 2 -> OS Repair, 3 -> Network.
``main.py`` maps the selected index to either the Fixer or a dashboard category.
"""
from __future__ import annotations

import flet as ft


def build_sidebar(on_change) -> ft.NavigationRail:
    """Create the NavigationRail. *on_change* receives the Flet change event."""
    return ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=96,
        min_extended_width=180,
        group_alignment=-0.9,
        leading=ft.Container(
            content=ft.Icon(ft.Icons.MEDICAL_SERVICES, size=28, color=ft.Colors.BLUE_300),
            padding=ft.padding.only(top=10, bottom=4),
        ),
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.AUTO_FIX_HIGH,
                selected_icon=ft.Icons.AUTO_FIX_HIGH,
                label="Fix My PC",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SYSTEM_UPDATE_ALT,
                selected_icon=ft.Icons.SYSTEM_UPDATE,
                label="Updates",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.HEALING_OUTLINED,
                selected_icon=ft.Icons.HEALING,
                label="OS Repair",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.LAN_OUTLINED,
                selected_icon=ft.Icons.LAN,
                label="Network",
            ),
        ],
        on_change=on_change,
    )
