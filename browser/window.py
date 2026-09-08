"""
Main application window: hosts the navigation bar and the tab widget,
and wires their signals together.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import QMainWindow, QSplitter, QVBoxLayout, QWidget, QLabel

from browser.debug_panel import DebugPanel
from browser.navigation import NavigationBar, resolve_input_to_url
from browser.profile import get_browser_profile
from browser.shortcuts import setup_shortcuts
from browser.tabs import TabWidget
from browser.webview import BrowserView
from config.settings import NEW_TAB_URL, Settings, get_settings
from utils.logger import get_logger

logger = get_logger(__name__)

class AIWorker(QThread):
    """Worker to fetch response from local Ollama without blocking UI."""
    finished = Signal(str)

    def __init__(self, settings: Settings, prompt: str, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._prompt = prompt

    def run(self) -> None:
        from ai.ollama import generate_response
        from browser.debug_log import DebugLog

        DebugLog.instance().log("AI", f"Request -> Send to AI: {self._prompt[:100]}...")
        result = generate_response(self._settings.ollama_url, self._settings.ollama_model, self._prompt)
        DebugLog.instance().log("AI", f"Response <- AI: {result[:100]}...")
        self.finished.emit(result)

_STYLESHEET = """
QMainWindow { background: #1e1f22; }

QWidget#navigationBar { background: #1e1f22; border-bottom: 1px solid #2c2d30; }

QPushButton#navButton {
    background: transparent;
    border: none;
    border-radius: 17px;
    color: #d6d7db;
    font-size: 15px;
}
QPushButton#navButton:hover { background: #2f3033; }
QPushButton#navButton:disabled { color: #55565a; }

QLineEdit#addressBar {
    background: #2a2b2e;
    border: 1px solid #3a3b3f;
    border-radius: 17px;
    padding: 6px 16px;
    color: #eaeaec;
    font-size: 14px;
}
QLineEdit#addressBar:focus { border: 1px solid #6ea8fe; }

QTabWidget::pane { border: none; }
QTabBar { background: #1a1b1d; }
QTabBar::tab {
    background: #1a1b1d;
    color: #9aa0a6;
    padding: 8px 18px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    min-width: 120px;
}
QTabBar::tab:selected { background: #2a2b2e; color: #eaeaec; }
QTabBar::tab:hover:!selected { background: #232427; }
QTabBar::close-button { subcontrol-position: right; }

QMenu {
    background: #26272a;
    border: 1px solid #3a3b3f;
    border-radius: 8px;
    padding: 4px;
    color: #eaeaec;
}
QMenu::item { padding: 7px 16px; border-radius: 5px; }
QMenu::item:selected { background: #35363a; }
QMenu::item:disabled { color: #6a6b6f; }
QMenu::separator { height: 1px; background: #3a3b3f; margin: 4px 8px; }

QSplitter::handle { background: #2c2d30; width: 2px; }

QWidget#debugPanel { background: #1a1b1d; }
QLabel#debugPanelTitle { color: #eaeaec; font-size: 13px; font-weight: 600; }
QLabel#debugPanelSubtitle { color: #9aa0a6; font-size: 11px; }
QPlainTextEdit#debugLogView {
    background: #101112;
    color: #c9cdd3;
    border: 1px solid #2c2d30;
    border-radius: 6px;
    padding: 8px;
}
"""


class MainWindow(QMainWindow):
    """Top-level MyBrowser window."""

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__()
        self._settings = settings or get_settings()

        self.setWindowTitle("MyBrowser")
        self.resize(self._settings.window_width, self._settings.window_height)
        self.setMinimumSize(800, 500)
        self.setStyleSheet(_STYLESHEET)

        self._profile = get_browser_profile(self._settings)

        browsing_area = QWidget(self)
        layout = QVBoxLayout(browsing_area)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.nav_bar = NavigationBar(self._settings, self)
        self.nav_bar.setObjectName("navigationBar")

        self.tabs = TabWidget(self._profile, self._settings, self)

        layout.addWidget(self.nav_bar)
        layout.addWidget(self.tabs, 1)

        # Debug Mode splits the window: browsing area on the left, a live
        # log of real AI/server request-response traffic on the right.
        # Hidden by default so normal browsing is completely unaffected.
        self.splitter = QSplitter(Qt.Horizontal, self)
        self.debug_panel = DebugPanel(self.splitter)
        self.splitter.addWidget(browsing_area)
        self.splitter.addWidget(self.debug_panel)
        self.debug_panel.setVisible(False)
        self.splitter.setCollapsible(0, False)
        self.setCentralWidget(self.splitter)

        self._connect_signals()
        self._shortcuts = setup_shortcuts(
            self,
            focus_address_bar=self.nav_bar.focus_address_bar,
            new_tab=lambda: self.tabs.new_tab(NEW_TAB_URL),
            close_tab=self.tabs.close_current_tab,
            reopen_closed_tab=self.tabs.reopen_last_closed_tab,
            reload_page=self._reload_current,
            go_back=self._go_back,
            go_forward=self._go_forward,
        )

        # Start with a single tab on the home page.
        self.tabs.new_tab(NEW_TAB_URL)

        logger.info("MyBrowser window initialized (%dx%d)", self.width(), self.height())

    # -- Wiring ---------------------------------------------------------------

    def _connect_signals(self) -> None:
        self.nav_bar.url_entered.connect(self._on_url_entered)
        self.nav_bar.back_clicked.connect(self._go_back)
        self.nav_bar.forward_clicked.connect(self._go_forward)
        self.nav_bar.reload_clicked.connect(self._reload_current)
        self.nav_bar.stop_clicked.connect(self._stop_current)
        self.nav_bar.home_clicked.connect(self._go_home)
        self.nav_bar.debug_mode_toggled.connect(self._on_debug_mode_toggled)
        self.tabs.current_view_changed.connect(self._on_current_view_changed)
        self.tabs.ai_request.connect(self._on_ai_request)

    def _on_ai_request(self, text: str) -> None:
        """Handle a request to send selected text to AI."""
        logger.info("MainWindow: _on_ai_request called with text: %s", text[:50] + "...")
        self.display_ai_response("Thinking…")

        self._ai_worker = AIWorker(self._settings, text, self)
        self._ai_worker.finished.connect(self.display_ai_response)
        self._ai_worker.start()

    def _current_view(self) -> BrowserView | None:
        return self.tabs.current_view()

    # -- Address bar / navigation handlers -------------------------------------

    def _on_url_entered(self, raw_text: str) -> None:
        view = self._current_view()
        if view is None:
            return
        url = resolve_input_to_url(raw_text, self._settings)
        view.navigate_to(url)

    def _go_back(self) -> None:
        view = self._current_view()
        if view:
            view.back()

    def _go_forward(self) -> None:
        view = self._current_view()
        if view:
            view.forward()

    def _reload_current(self) -> None:
        view = self._current_view()
        if view:
            view.reload()

    def _stop_current(self) -> None:
        view = self._current_view()
        if view:
            view.stop()

    def _go_home(self) -> None:
        view = self._current_view()
        if view:
            view.navigate_to(self._settings.home_page)

    def _on_debug_mode_toggled(self, enabled: bool) -> None:
        """Show/hide the debug traffic panel by splitting the window."""
        self.debug_panel.setVisible(enabled)
        if enabled:
            total_width = max(self.width(), 800)
            self.splitter.setSizes([int(total_width * 0.65), int(total_width * 0.35)])
        logger.info("Debug mode %s", "enabled" if enabled else "disabled")

    # -- Per-tab UI sync --------------------------------------------------------

    def _on_current_view_changed(self, view: BrowserView | None) -> None:
        if view is None:
            return

        self._sync_nav_bar_for(view)

        # Reconnect UI-sync signals for whichever tab is now active. Using
        # a per-view attribute guards against connecting the same slot twice.
        if not getattr(view, "_ui_synced", False):
            view.url_changed_str.connect(lambda url, v=view: self._maybe_sync(v, url))
            view.loadStarted.connect(lambda v=view: self._maybe_sync_loading(v, True))
            view.loadFinished.connect(lambda ok, v=view: self._maybe_sync_loading(v, False))
            view._ui_synced = True  # type: ignore[attr-defined]

    def _maybe_sync(self, view: BrowserView, url: str) -> None:
        if view is self._current_view():
            display_url = "" if url == NEW_TAB_URL else url
            self.nav_bar.set_url_text(display_url)
            self.nav_bar.set_nav_buttons_enabled(view.history().canGoBack(), view.history().canGoForward())

    def _maybe_sync_loading(self, view: BrowserView, is_loading: bool) -> None:
        if view is self._current_view():
            self.nav_bar.set_loading_state(is_loading)
            self.nav_bar.set_nav_buttons_enabled(view.history().canGoBack(), view.history().canGoForward())

    def _sync_nav_bar_for(self, view: BrowserView) -> None:
        url = view.url().toString()
        self.nav_bar.set_url_text("" if url == NEW_TAB_URL else url)
        self.nav_bar.set_nav_buttons_enabled(view.history().canGoBack(), view.history().canGoForward())

    # -- Qt overrides -------------------------------------------------------

    def display_ai_response(self, text: str) -> None:
        """Show the AI response in a floating label at the bottom-right."""
        if not hasattr(self, "_ai_response_label"):
            self._ai_response_label = QLabel(self)
            self._ai_response_label.setFixedSize(60, 30)
            self._ai_response_label.setWordWrap(True)
            self._ai_response_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            self._ai_response_label.setStyleSheet('''
                background: rgba(30, 31, 34, 150);
                color: #eaeaec;
                border: 1px solid #3a3b3f;
                border-radius: 12px;
                padding: 8px;
                font-size: 12px;
                font-family: "Segoe UI", Roboto, Arial, sans-serif;
            ''')
            self._ai_response_label.hide()

        self._ai_response_label.setText(text)
        # Position it at the bottom-right
        self._ai_response_label.move(
            10,
            self.height() - self._ai_response_label.height() - 10
        )
        self._ai_response_label.show()
        self._ai_response_label.raise_()

    def resizeEvent(self, event) -> None:
        if hasattr(self, "_ai_response_label") and self._ai_response_label.isVisible():
            self._ai_response_label.move(
                self.width() - self._ai_response_label.width() - 20,
                self.height() - self._ai_response_label.height() - 20
            )
        super().resizeEvent(event)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)

        self._settings.window_width = self.width()
        self._settings.window_height = self.height()
        self._settings.save()
        super().closeEvent(event)
