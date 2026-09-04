"""
Keyboard shortcuts for the main window.

All shortcuts here use modifier keys (Ctrl/Alt) or function keys, so they
never collide with normal text entry in the address bar or on web pages
(e.g. Ctrl+W does not type the letter "w"). Because of that they are safe
to register at the window level with Qt's default shortcut context.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QWidget


def setup_shortcuts(
    window: QWidget,
    *,
    focus_address_bar: Callable[[], None],
    new_tab: Callable[[], None],
    close_tab: Callable[[], None],
    reopen_closed_tab: Callable[[], None],
    reload_page: Callable[[], None],
    go_back: Callable[[], None],
    go_forward: Callable[[], None],
) -> list[QShortcut]:
    """Create and return all QShortcut objects (kept alive by the caller)."""

    bindings: list[tuple[str, Callable[[], None]]] = [
        ("Ctrl+L", focus_address_bar),
        ("Ctrl+T", new_tab),
        ("Ctrl+W", close_tab),
        ("Ctrl+R", reload_page),
        ("F5", reload_page),
        ("Ctrl+Shift+T", reopen_closed_tab),
        ("Alt+Left", go_back),
        ("Alt+Right", go_forward),
    ]

    shortcuts = []
    for key_sequence, handler in bindings:
        shortcut = QShortcut(QKeySequence(key_sequence), window)
        shortcut.activated.connect(handler)
        shortcuts.append(shortcut)

    return shortcuts
