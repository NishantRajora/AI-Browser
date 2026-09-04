"""
Tab management: new/close/switch/reorder tabs, titles, favicons,
and "reopen last closed tab".
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon
from PySide6.QtWebEngineCore import QWebEngineProfile
from PySide6.QtWidgets import QTabWidget

from browser.webview import BrowserView
from config.settings import NEW_TAB_URL, Settings
from utils.logger import get_logger

logger = get_logger(__name__)

_MAX_CLOSED_TAB_HISTORY = 10
_DEFAULT_TAB_TITLE = "New Tab"
_MAX_TAB_TITLE_LEN = 24


class TabWidget(QTabWidget):
    """A QTabWidget specialized for browser tabs, each holding a BrowserView."""

    current_view_changed = Signal(object)  # emits the now-active BrowserView

    def __init__(self, profile: QWebEngineProfile, settings: Settings, parent=None) -> None:
        super().__init__(parent)
        self._profile = profile
        self._settings = settings
        self._closed_tab_urls: list[str] = []

        self.setTabsClosable(True)
        self.setMovable(True)  # drag-to-reorder tabs
        self.setDocumentMode(True)
        self.setElideMode__safe()

        self.tabCloseRequested.connect(self.close_tab)
        self.currentChanged.connect(self._on_current_changed)

    def setElideMode__safe(self) -> None:
        # Small helper kept separate so intent is documented; elides long titles.
        from PySide6.QtCore import Qt

        self.setElideMode(Qt.ElideRight)

    # -- Tab lifecycle -----------------------------------------------------

    def new_tab(self, url: str | None = None, make_current: bool = True) -> BrowserView:
        """Create a new tab loading `url` (or the new-tab page) and return its view."""
        view = BrowserView(self._profile)
        view.title_changed.connect(lambda title, v=view: self._on_title_changed(v, title))
        view.icon_changed.connect(lambda v=view: self._on_icon_changed(v))
        view.loadStarted.connect(lambda v=view: self._on_load_started(v))
        view.loadFinished.connect(lambda ok, v=view: self._on_load_finished(v, ok))

        index = self.addTab(view, _DEFAULT_TAB_TITLE)
        target = url or self._settings.home_page
        view.navigate_to(target if target else NEW_TAB_URL)

        if make_current:
            self.setCurrentIndex(index)

        logger.info("Opened new tab (index=%d) -> %s", index, target)
        return view

    def close_tab(self, index: int) -> None:
        """Close the tab at `index`. Never lets the window end up with zero tabs."""
        if index < 0 or index >= self.count():
            return

        view = self.widget(index)
        closed_url = view.url().toString() if hasattr(view, "url") else ""
        if closed_url and closed_url != NEW_TAB_URL:
            self._closed_tab_urls.append(closed_url)
            del self._closed_tab_urls[:-_MAX_CLOSED_TAB_HISTORY]

        self.removeTab(index)
        view.deleteLater()
        logger.info("Closed tab (index=%d) -> %s", index, closed_url)

        if self.count() == 0:
            # Never leave the browser with no tabs at all.
            self.new_tab(NEW_TAB_URL)

    def reopen_last_closed_tab(self) -> None:
        if not self._closed_tab_urls:
            logger.info("No closed tab to reopen.")
            return
        url = self._closed_tab_urls.pop()
        self.new_tab(url)

    def close_current_tab(self) -> None:
        self.close_tab(self.currentIndex())

    # -- Convenience accessors ----------------------------------------------

    def current_view(self) -> BrowserView | None:
        widget = self.currentWidget()
        return widget if isinstance(widget, BrowserView) else None

    # -- Signal handlers -----------------------------------------------------

    def _on_current_changed(self, index: int) -> None:
        self.current_view_changed.emit(self.current_view())

    def _on_title_changed(self, view: BrowserView, title: str) -> None:
        index = self.indexOf(view)
        if index == -1:
            return
        display_title = title.strip() or _DEFAULT_TAB_TITLE
        if len(display_title) > _MAX_TAB_TITLE_LEN:
            display_title = display_title[: _MAX_TAB_TITLE_LEN - 1] + "\u2026"
        self.setTabText(index, display_title)
        self.setTabToolTip(index, title)

    def _on_icon_changed(self, view: BrowserView) -> None:
        index = self.indexOf(view)
        if index == -1:
            return
        icon: QIcon = view.icon()
        if not icon.isNull():
            self.setTabIcon(index, icon)

    def _on_load_started(self, view: BrowserView) -> None:
        index = self.indexOf(view)
        if index != -1:
            self.setTabText(index, "Loading\u2026")

    def _on_load_finished(self, view: BrowserView, ok: bool) -> None:
        index = self.indexOf(view)
        if index == -1:
            return
        if not ok:
            self.setTabText(index, "Failed to load")
