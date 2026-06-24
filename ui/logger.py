"""StatusConsole — a read-only, streaming output console.

Implements the required real-time feedback widget: a read-only
``flet.TextField`` that updates via ``page.update()`` as a subprocess streams
stdout. It keeps the full log in memory (and can save it to disk) while showing
a rolling tail, so the newest output is always visible and rendering stays fast
even on huge SFC/DISM dumps.

The public ``append`` method *is* the ``emit`` callback handed to
``core.executor.run_command``.
"""
from __future__ import annotations

import datetime
import os

import flet as ft

# Cap what the TextField renders; the full history is still kept in memory and
# written to disk. Keeps the UI responsive during very long scans.
_MAX_VISIBLE_CHARS = 60_000


class StatusConsole:
    def __init__(self, page: ft.Page):
        self.page = page
        self._buffer: list[str] = []  # complete history (never truncated)

        # --- status header -------------------------------------------------
        self.status_icon = ft.Icon(ft.Icons.CIRCLE, color=ft.Colors.GREY, size=13)
        self.status_text = ft.Text("Idle", weight=ft.FontWeight.BOLD, size=13)
        self.spinner = ft.ProgressRing(
            width=15, height=15, stroke_width=2, visible=False
        )

        # --- the required read-only streaming TextField --------------------
        self.output = ft.TextField(
            value="Welcome to WHome Diagnostic Tool.\n"
                  "Select a tool on the left and press Run.\n"
                  "Safe Mode is ON — turn it off to perform real repairs.\n",
            read_only=True,
            multiline=True,
            min_lines=22,
            max_lines=22,
            text_size=12,
            text_style=ft.TextStyle(font_family="Consolas, monospace"),
            border_color=ft.Colors.TRANSPARENT,
            bgcolor=ft.Colors.BLACK,
            color=ft.Colors.GREEN_300,
            expand=True,
        )

        header = ft.Row(
            [
                self.status_icon,
                self.status_text,
                self.spinner,
                ft.Container(expand=True),
                ft.IconButton(
                    ft.Icons.SAVE_OUTLINED, tooltip="Save log to file",
                    icon_size=18, on_click=self._on_save,
                ),
                ft.IconButton(
                    ft.Icons.DELETE_OUTLINE, tooltip="Clear console",
                    icon_size=18, on_click=self._on_clear,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.view = ft.Container(
            content=ft.Column([header, self.output], spacing=8, expand=True),
            padding=12,
            border_radius=10,
            bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.WHITE),
            border=ft.border.all(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE)),
            expand=True,
        )

    # ------------------------------------------------------------------ #
    # Stream handling                                                    #
    # ------------------------------------------------------------------ #
    def append(self, text: str) -> None:
        """Append streamed output and refresh the UI.

        This is the ``emit`` callback passed to the executor. It is invoked from
        the asyncio task on Flet's own event loop, so calling ``page.update()``
        here is safe.
        """
        if not text:
            return
        self._buffer.append(text)
        full = "".join(self._buffer)
        # Show only the tail so the newest line stays visible and the control
        # stays fast even with megabytes of output.
        self.output.value = full[-_MAX_VISIBLE_CHARS:]
        self.page.update()

    def clear(self) -> None:
        self._buffer.clear()
        self.output.value = ""
        self.page.update()

    def set_running(self, running: bool, label: str = "") -> None:
        """Toggle the busy indicator in the header."""
        self.spinner.visible = running
        if running:
            self.status_icon.color = ft.Colors.AMBER
            self.status_text.value = f"Running: {label}" if label else "Running…"
        else:
            self.status_icon.color = ft.Colors.GREEN
            self.status_text.value = "Idle"
        self.page.update()

    # ------------------------------------------------------------------ #
    # Buttons                                                            #
    # ------------------------------------------------------------------ #
    def _on_clear(self, _e) -> None:
        self.clear()

    def _on_save(self, _e) -> None:
        try:
            path = self.save_to_disk()
            self.append(f"\n[log saved to {path}]\n")
        except Exception as exc:  # noqa: BLE001
            self.append(f"\n[could not save log: {exc}]\n")

    def save_to_disk(self) -> str:
        """Write the full history to ``~/WHomeDiagnostics-Logs`` and return path."""
        logs_dir = os.path.join(os.path.expanduser("~"), "WHomeDiagnostics-Logs")
        os.makedirs(logs_dir, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        path = os.path.join(logs_dir, f"diagnostic-{stamp}.log")
        with open(path, "w", encoding="utf-8", errors="replace") as fh:
            fh.write("".join(self._buffer))
        return path
