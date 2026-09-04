"""
Navigation bar: back/forward/reload/stop/home buttons + address bar.

The URL-vs-search decision logic is implemented as a plain function
(`resolve_input_to_url`) with no Qt dependency, so it can be unit tested
without a QApplication or a display.
"""

from __future__ import annotations

import re
from urllib.parse import quote_plus

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QSizePolicy, QWidget

from browser.menu import MoreOptionsButton
from config.settings import Settings
from utils.logger import get_logger

logger = get_logger(__name__)

# A very small, pragmatic heuristic for "this looks like a domain/host".
# Matches things like: google.com, sub.example.co.uk, localhost:8000, 192.168.1.1
_DOMAIN_LIKE_RE = re.compile(
    r"^(localhost(:\d+)?|(\d{1,3}\.){3}\d{1,3}(:\d+)?|"
    r"[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+(:\d+)?)(/.*)?$"
)


def resolve_input_to_url(raw_text: str, settings: Settings) -> str:
    """
    Turn whatever the user typed in the address bar into a navigable URL.

    Rules (checked in order):
      1. Empty input -> the configured home page.
      2. Already has a URL scheme (http://, https://, file://, mybrowser://) -> used as-is.
      3. Looks like a bare domain/host (e.g. "google.com", "localhost:8000") -> prefix "https://".
      4. Otherwise -> treated as a search query against the configured search engine.
    """
    text = raw_text.strip()
    if not text:
        return settings.home_page

    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", text):
        return text

    # "google.com" or "www.github.com/some/path" but not "python tutorials"
    if " " not in text and _DOMAIN_LIKE_RE.match(text):
        return f"https://{text}"

    query = quote_plus(text)
    return settings.search_engine_url.format(query=query)


class NavigationBar(QWidget):
    """Toolbar containing back/forward/reload/stop/home and the address bar."""

    back_clicked = Signal()
    forward_clicked = Signal()
    reload_clicked = Signal()
    stop_clicked = Signal()
    home_clicked = Signal()
    url_entered = Signal(str)  # emits raw text typed by the user
    debug_mode_toggled = Signal(bool)

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._is_loading = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        self.back_button = self._make_nav_button("\u2190", "Back (Alt+Left)")
        self.forward_button = self._make_nav_button("\u2192", "Forward (Alt+Right)")
        self.reload_button = self._make_nav_button("\u21bb", "Reload (Ctrl+R / F5)")
        self.home_button = self._make_nav_button("\u2302", "Home")

        self.address_bar = QLineEdit(self)
        self.address_bar.setObjectName("addressBar")
        self.address_bar.setPlaceholderText("Search or enter address")
        self.address_bar.setClearButtonEnabled(True)
        self.address_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.address_bar.returnPressed.connect(self._on_return_pressed)

        self.more_options_button = MoreOptionsButton(self._settings, self)
        self.more_options_button.debug_mode_toggled.connect(self.debug_mode_toggled.emit)

        self.back_button.clicked.connect(self.back_clicked.emit)
        self.forward_button.clicked.connect(self.forward_clicked.emit)
        self.reload_button.clicked.connect(self._on_reload_or_stop)
        self.home_button.clicked.connect(self.home_clicked.emit)

        layout.addWidget(self.back_button)
        layout.addWidget(self.forward_button)
        layout.addWidget(self.reload_button)
        layout.addWidget(self.home_button)
        layout.addWidget(self.address_bar, 1)
        layout.addWidget(self.more_options_button)

    @staticmethod
    def _make_nav_button(label: str, tooltip: str) -> QPushButton:
        button = QPushButton(label)
        button.setObjectName("navButton")
        button.setFixedSize(34, 34)
        button.setToolTip(tooltip)
        button.setCursor(Qt.PointingHandCursor)
        return button

    def _on_return_pressed(self) -> None:
        self.url_entered.emit(self.address_bar.text())

    def _on_reload_or_stop(self) -> None:
        if self._is_loading:
            self.stop_clicked.emit()
        else:
            self.reload_clicked.emit()

    def set_loading_state(self, is_loading: bool) -> None:
        """Swap the reload button between 'reload' and 'stop' glyphs."""
        self._is_loading = is_loading
        self.reload_button.setText("\u2715" if is_loading else "\u21bb")
        self.reload_button.setToolTip("Stop loading" if is_loading else "Reload (Ctrl+R / F5)")

    def set_url_text(self, url_text: str) -> None:
        """Update the address bar text without emitting url_entered."""
        if not self.address_bar.hasFocus():
            self.address_bar.setText(url_text)
            self.address_bar.setCursorPosition(0)

    def set_nav_buttons_enabled(self, can_go_back: bool, can_go_forward: bool) -> None:
        self.back_button.setEnabled(can_go_back)
        self.forward_button.setEnabled(can_go_forward)

    def focus_address_bar(self) -> None:
        self.address_bar.setFocus()
        self.address_bar.selectAll()
