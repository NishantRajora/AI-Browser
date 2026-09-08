"""
Main application window: hosts the navigation bar and the tab widget,
and wires their signals together.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QThread, QPoint
from PySide6.QtWidgets import QMainWindow, QSplitter, QVBoxLayout, QHBoxLayout, QWidget, QLabel

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

    def __init__(self, settings: Settings, prompt: str, label: str = "AI", parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._prompt = prompt
        self._label = label

    def run(self) -> None:
        from ai.ollama import generate_response
        from browser.debug_log import DebugLog

        DebugLog.instance().log(self._label, f"Request -> {self._prompt[:100]}...")
        result = generate_response(self._settings.ollama_url, self._settings.ollama_model, self._prompt)
        DebugLog.instance().log(self._label, f"Response <- {result[:100]}...")
        self.finished.emit(result)

_STYLESHEET = """
QMainWindow { background: #202124; }

QWidget#navigationBar {
    background: #202124;
    border-bottom: 1px solid #3c4043;
}

QPushButton#navButton {
    background: transparent;
    border: none;
    border-radius: 16px;
    color: #bdc1c6;
    font-size: 16px;
    padding: 4px;
}
QPushButton#navButton:hover { background: #3c4043; }
QPushButton#navButton:disabled { color: #5f6368; }

QLineEdit#addressBar {
    background: #292a2d;
    border: 1px solid #3c4043;
    border-radius: 16px;
    padding: 6px 16px;
    color: #e8eaed;
    font-size: 14px;
    selection-background-color: #4d7be6;
}
QLineEdit#addressBar:focus { border: 1px solid #8ab4f8; background: #202124; }

QTabWidget::pane {
    border: none;
    top: -1px;
}
QTabBar {
    background: #202124;
    border-bottom: 1px solid #3c4043;
}
QTabBar::tab {
    background: #202124;
    color: #9aa0a6;
    padding: 8px 12px;
    margin-top: 8px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    min-width: 150px;
    border: none;
}
QTabBar::tab:selected {
    background: #35363a;
    color: #e8eaed;
    font-weight: 500;
}
QTabBar::tab:hover:!selected { background: #292a2d; }
QTabBar::close-button {
    subcontrol-position: right;
    image: none;
}

QMenu {
    background: #2d2e31;
    border: 1px solid #3c4043;
    border-radius: 8px;
    padding: 4px;
    color: #e8eaed;
}
QMenu::item { padding: 8px 24px 8px 16px; border-radius: 4px; }
QMenu::item:selected { background: #3c4043; }
QMenu::item:disabled { color: #5f6368; }
QMenu::separator { height: 1px; background: #3c4043; margin: 4px 0; }

QSplitter::handle { background: #3c4043; width: 1px; }

QWidget#debugPanel { background: #1a1b1d; }
QLabel#debugPanelTitle { color: #e8eaed; font-size: 13px; font-weight: 600; }
QLabel#debugPanelSubtitle { color: #9aa0a6; font-size: 11px; }
QPlainTextEdit#debugLogView {
    background: #101112;
    color: #c9cdd3;
    border: 1px solid #3c4043;
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

        # Initialize core components before layout construction
        self.tabs = TabWidget(self._profile, self._settings, self)
        self.nav_bar = NavigationBar(self._settings, self)

        browsing_area = QWidget(self)
        # Main layout
        main_layout = QVBoxLayout(browsing_area)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Chromium-style layout: Tab Bar on top, then Nav Bar, then Content
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)

        # Tab bar layout (Tabs + Add button)
        tab_bar_container = QWidget()
        tab_bar_layout = QHBoxLayout(tab_bar_container)
        tab_bar_layout.setContentsMargins(0, 0, 0, 0)
        tab_bar_layout.setSpacing(0)
        tab_bar_layout.addWidget(self.tabs.tab_bar)
        tab_bar_layout.addWidget(self.tabs.add_tab_button)

        top_layout.addWidget(tab_bar_container)
        top_layout.addWidget(self.nav_bar)

        # Now add the stacked content area
        main_layout.addWidget(top_widget)
        main_layout.addWidget(self.tabs.content_area)

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

        # Connect TabWidget's add button to the new_tab method
        self.tabs.add_tab_button.clicked.connect(lambda: self.tabs.new_tab())

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
        self.tabs.full_page_request.connect(self._on_full_page_request)

    def _on_ai_request(self, text: str, pos: QPoint) -> None:
        """Handle a request to send selected text to AI."""
        from ai.prompts import build_selected_text_prompt

        self.display_ai_response("Scanning...", pos=pos)

        prompt = build_selected_text_prompt(text)
        self._ai_worker = AIWorker(self._settings, prompt, label="SEND SELECTED TEXT TO AI", parent=self)
        self._ai_worker.finished.connect(self.display_ai_response)
        self._ai_worker.start()

    def _on_full_page_request(self, pos: QPoint) -> None:
        """Handle a request to send the whole page content to AI."""
        view = self._current_view()
        if view is None:
            self.display_ai_response("Unable to determine", pos=pos)
            return

        self.display_ai_response("Scanning...", pos=pos)

        # Extract readable text asynchronously
        js_code = "document.body.innerText"
        view.page().runJavaScript(js_code, lambda result: self._process_full_page_result(result, pos))

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

    def _hide_ai_response(self) -> None:
        """Hide the AI response popup."""
        if hasattr(self, "_ai_response_label"):
            self._ai_response_label.hide()

    def _on_current_view_changed(self, view: BrowserView | None) -> None:
        if view is None:
            return

        self._sync_nav_bar_for(view)

        # Reconnect UI-sync signals for whichever tab is now active. Using
        # a per-view attribute guards against connecting the same slot twice.
        if not getattr(view, "_ui_synced", False):
            view.url_changed_str.connect(lambda url, v=view: self._maybe_sync(v, url))
            view.loadStarted.connect(lambda v=view: self._maybe_sync_loading(v, True))
            view.loadStarted.connect(self._hide_ai_response)
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

    def display_ai_response(self, text: str, pos: QPoint = None) -> None:
        """Show the AI response in a small, clean floating popup."""
        if not hasattr(self, "_ai_response_label"):
            self._ai_response_label = QLabel(self)
            self._ai_response_label.setMinimumSize(0, 0)
            self._ai_response_label.setMaximumWidth(300)
            self._ai_response_label.setWordWrap(True)
            self._ai_response_label.setAlignment(Qt.AlignCenter)
            # Style for a native-feeling tooltip
            self._ai_response_label.setStyleSheet('''
                QLabel {
                    background-color: #2a2b2e;
                    color: #eaeaec;
                    border: 1px solid #3a3b3f;
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-size: 13px;
                    font-weight: 600;
                    font-family: "Segoe UI", Roboto, Arial, sans-serif;
                }
            ''')
            self._ai_response_label.hide()

        # Handle special states
        stripped_text = text.strip()
        if stripped_text.startswith("Error:"):
            final_text = "AI unavailable"
        elif stripped_text == "NO_QUESTION":
            final_text = "No question detected"
        elif stripped_text == "UNCERTAIN":
            final_text = "Unable to determine"
        elif stripped_text in ("Scanning...", "Thinking…"):
            final_text = "Scanning..."
        elif stripped_text == "Unable to determine":
            final_text = "Unable to determine"
        else:
            final_text = self._clean_answer(stripped_text)

        self._ai_response_label.setText(final_text)
        self._ai_response_label.adjustSize()

        # Positioning
        if pos:
            # Convert global position to window-relative position
            relative_pos = self.mapFromGlobal(pos)
            # Offset slightly so it doesn't cover the cursor
            self._ai_response_label.move(relative_pos.x() + 10, relative_pos.y() + 10)
        else:
            # Default to bottom-right if no position provided
            self._ai_response_label.move(
                self.width() - self._ai_response_label.width() - 20,
                self.height() - self._ai_response_label.height() - 20
            )

        self._ai_response_label.show()
        self._ai_response_label.raise_()

    def _clean_answer(self, text: str) -> str:
        """Remove Markdown formatting from the LLM answer."""
        import re
        # Remove code fences
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        # Remove inline code
        text = re.sub(r'`[^`]*`', '', text)
        # Remove blockquotes
        text = re.sub(r'>\s*', '', text)
        # Remove bullet list markers
        text = re.sub(r'^[\-\*•]\s+', '', text, flags=re.MULTILINE)
        # Remove headers
        text = re.sub(r'^[#]+[\s]*', '', text, flags=re.MULTILINE)
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)

    def _process_full_page_result(self, content: str, pos: QPoint) -> None:
        """Callback for JavaScript extraction of full page content."""
        from ai.prompts import build_full_page_prompt

        if not content or not content.strip():
            self.display_ai_response("Unable to determine", pos=pos)
            return

        # Basic cleaning: remove excessive whitespace
        import re
        cleaned_content = re.sub(r'\n\s*\n', '\n\n', content.strip())

        prompt = build_full_page_prompt(cleaned_content)
        self._ai_worker = AIWorker(self._settings, prompt, label="SEND WHOLE PAGE TO AI", parent=self)
        self._ai_worker.finished.connect(self.display_ai_response)
        self._ai_worker.start()

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)

        self._settings.window_width = self.width()
        self._settings.window_height = self.height()
        self._settings.save()
        super().closeEvent(event)
