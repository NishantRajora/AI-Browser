"""
Tab management: new/close/switch/reorder tabs, titles, favicons,
and "reopen last closed tab".
"""

from __future__ import annotations

from PySide6.QtCore import Signal, QPoint, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWebEngineCore import QWebEngineProfile
from PySide6.QtWidgets import QWidget, QTabBar, QStackedWidget, QPushButton

from browser.webview import BrowserView
from config.settings import NEW_TAB_URL, Settings
from utils.logger import get_logger

logger = get_logger(__name__)

_MAX_CLOSED_TAB_HISTORY = 10
_DEFAULT_TAB_TITLE = "New Tab"
_MAX_TAB_TITLE_LEN = 24


class TabWidget(QWidget):
    """Manages browser tabs using a separate QTabBar and QStackedWidget."""

    current_view_changed = Signal(object)  # emits the now-active BrowserView
    ai_request = Signal(str, QPoint)
    full_page_request = Signal(QPoint)

    def __init__(self, profile: QWebEngineProfile, settings: Settings, parent=None) -> None:
        super().__init__(parent)
        self._profile = profile
        self._settings = settings
        self._closed_tab_urls: list[str] = []

        # Tab Bar
        self.tab_bar = QTabBar(self)
        self.tab_bar.setMovable(True)
        self.tab_bar.setExpanding(False)

        # Content Area
        self.content_area = QStackedWidget(self)

        # New Tab (+) button
        self.add_tab_button = QPushButton("+")
        self.add_tab_button.setFixedSize(30, 20)
        self.add_tab_button.setToolTip("New Tab (Ctrl+T)")
        self.add_tab_button.setCursor(Qt.PointingHandCursor)

        # Connect signals
        self.tab_bar.currentChanged.connect(self._on_current_changed)
        self.tab_bar.tabCloseRequested.connect(self.close_tab)

    def setElideMode__safe(self) -> None:
        # No longer needed as QTabBar handles eliding differently or we use lapped text
        pass

    # -- Tab lifecycle -----------------------------------------------------

    def new_tab(self, url: str | None = None, make_current: bool = True) -> BrowserView:
        """Create a new tab loading `url` (or the new-tab page) and return its view."""
        view = BrowserView(self._profile)
        view.title_changed.connect(lambda title, v=view: self._on_title_changed(v, title))
        view.icon_changed.connect(lambda v=view: self._on_icon_changed(v))
        view.loadStarted.connect(lambda v=view: self._on_load_started(v))
        view.loadFinished.connect(lambda ok, v=view: self._on_load_finished(v, ok))
        view.ai_request.connect(self._handle_view_ai_request)
        view.full_page_request.connect(self._handle_view_full_page_request)

        index = self.tab_bar.addTab(_DEFAULT_TAB_TITLE)
        self.content_area.addWidget(view)

        target = url or self._settings.home_page
        view.navigate_to(target if target else NEW_TAB_URL)

        if make_current:
            self.tab_bar.setCurrentIndex(index)
            self.content_area.setCurrentIndex(index)

        logger.info("Opened new tab (index=%d) -> %s", index, target)
        return view

    def _handle_view_ai_request(self, text: str, pos: QPoint) -> None:
        logger.info("TabWidget: received ai_request from view, emitting to window")
        self.ai_request.emit(text, pos)

    def _handle_view_full_page_request(self, pos: QPoint) -> None:
        logger.info("TabWidget: received full_page_request from view, emitting to window")
        self.full_page_request.emit(pos)

    def close_tab(self, index: int) -> None:
        """Close the tab at `index`."""
        if index < 0 or index >= self.tab_bar.count():
            return

        view = self.content_area.widget(index)
        closed_url = view.url().toString() if hasattr(view, "url") else ""
        if closed_url and closed_url != NEW_TAB_URL:
            self._closed_tab_urls.append(closed_url)
            del self._closed_tab_urls[:-_MAX_CLOSED_TAB_HISTORY]

        self.tab_bar.removeTab(index)
        self.content_area.removeWidget(view)
        view.deleteLater()
        logger.info("Closed tab (index=%d) -> %s", index, closed_url)

        if self.tab_bar.count() == 0:
            self.new_tab(NEW_TAB_URL)

    def reopen_last_closed_tab(self) -> None:
        if not self._closed_tab_urls:
            logger.info("No closed tab to reopen.")
            return
        url = self._closed_tab_urls.pop()
        self.new_tab(url)

    def close_current_tab(self) -> None:
        self.close_tab(self.tab_bar.currentIndex())

    # -- Convenience accessors ----------------------------------------------

    def current_view(self) -> BrowserView | None:
        index = self.tab_bar.currentIndex()
        if index < 0:
            return None
        return self.content_area.widget(index) if isinstance(self.content_area.widget(index), BrowserView) else None

    # -- Signal handlers -----------------------------------------------------

    def _on_current_changed(self, index: int) -> None:
        self.content_area.setCurrentIndex(index)
        self.current_view_changed.emit(self.current_view())

    def _on_title_changed(self, view: BrowserView, title: str) -> None:
        index = self.content_area.indexOf(view)
        if index == -1:
            return
        display_title = title.strip() or _DEFAULT_TAB_TITLE
        if len(display_title) > _MAX_TAB_TITLE_LEN:
            display_title = display_title[: _MAX_TAB_TITLE_LEN - 1] + "…"
        self.tab_bar.setTabText(index, display_title)
        self.tab_bar.setTabToolTip(index, title)

    def _on_icon_changed(self, view: BrowserView) -> None:
        index = self.content_area.indexOf(view)
        if index == -1:
            return
        icon: QIcon = view.icon()
        if not icon.isNull():
            self.tab_bar.setTabIcon(index, icon)

    def _on_load_started(self, view: BrowserView) -> None:
        index = self.content_area.indexOf(view)
        if index != -1:
            self.tab_bar.setTabText(index, "Loading…")

    def _on_load_finished(self, view: BrowserView, ok: bool) -> None:
        index = self.content_area.indexOf(view)
        if index == -1:
            return
        if not ok:
            self.tab_bar.setTabText(index, "Failed to load")
