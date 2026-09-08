"""
The actual Chromium-rendered page widget, plus the custom New Tab page.

MyBrowser renders real websites with QWebEngineView (Chromium) — nothing
here fakes rendering with a custom HTML layout engine.
"""

from __future__ import annotations

from PySide6.QtCore import QUrl, Signal, QPoint
from PySide6.QtGui import QAction
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QMenu

from config.settings import NEW_TAB_URL, get_settings
from utils.logger import get_logger

logger = get_logger(__name__)



_NEW_TAB_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>New Tab</title>
<style>
    :root {{ color-scheme: light dark; }}
    body {{
        margin: 0;
        height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #1e1f22;
        font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
        color: #e8e8ea;
    }}
    .card {{ text-align: center; width: 560px; max-width: 90vw; }}
    .logo {{
        font-size: 34px;
        font-weight: 700;
        letter-spacing: -0.5px;
        margin-bottom: 28px;
        color: #6ea8fe;
    }}
    form {{ display: flex; }}
    input[type="text"] {{
        flex: 1;
        padding: 14px 20px;
        font-size: 15px;
        border-radius: 24px;
        border: 1px solid #3a3b3f;
        background: #2a2b2e;
        color: #e8e8ea;
        outline: none;
    }}
    input[type="text"]:focus {{ border-color: #6ea8fe; }}
    .links {{
        margin-top: 26px;
        display: flex;
        gap: 14px;
        justify-content: center;
        flex-wrap: wrap;
    }}
    .links a {{
        color: #9aa0a6;
        text-decoration: none;
        font-size: 13px;
        padding: 6px 12px;
        border-radius: 12px;
        background: #2a2b2e;
    }}
    .links a:hover {{ background: #35363a; color: #e8e8ea; }}
</style>
</head>
<body>
    <div class="card">
        <div class="logo">MyBrowser</div>
        <form action="{search_action}" method="get">
            <input type="text" name="q" placeholder="Search or enter address" autofocus>
        </form>
        <div class="links">
            {quick_links}
        </div>
    </div>
</body>
</html>
"""


def build_new_tab_html(search_engine_url: str, quick_links: list[tuple[str, str]]) -> str:
    """
    Render the new-tab page HTML.

    quick_links: list of (label, url) tuples shown as small pill buttons.
    """
    # The settings store search_engine_url as ".../search?q={query}"; the
    # plain HTML <form> needs a base action without the placeholder.
    action = search_engine_url.split("{query}")[0] if "{query}" in search_engine_url else search_engine_url
    links_html = "".join(f'<a href="{url}">{label}</a>' for label, url in quick_links) or (
        '<a href="https://github.com">GitHub</a>'
        '<a href="https://youtube.com">YouTube</a>'
        '<a href="https://python.org">Python</a>'
    )
    return _NEW_TAB_HTML.format(search_action=action, quick_links=links_html)


class BrowserPage(QWebEnginePage):
    """QWebEnginePage subclass so we can hook JS console messages for debugging."""

    def javaScriptConsoleMessage(self, level, message, line_number, source_id):  # noqa: N802 (Qt override)
        # Keep this quiet by default; flip to logger.debug during development.
        pass


class BrowserView(QWebEngineView):
    """A single Chromium view representing the content of one tab."""

    title_changed = Signal(str)
    icon_changed = Signal()
    url_changed_str = Signal(str)
    ai_request = Signal(str, QPoint)
    full_page_request = Signal(QPoint)

    def __init__(self, profile: QWebEngineProfile, parent=None) -> None:
        super().__init__(parent)
        page = BrowserPage(profile, self)
        self.setPage(page)

        self.titleChanged.connect(self.title_changed.emit)
        self.iconChanged.connect(self.icon_changed.emit)
        self.urlChanged.connect(lambda qurl: self.url_changed_str.emit(qurl.toString()))
        self.loadFinished.connect(self._on_load_finished)

    def contextMenuEvent(self, event) -> None:
        """Custom context menu for AI features."""
        selected_text = self.page().selectedText()

        # Create a custom menu
        menu = QMenu(self)

        # 1. "Send Selected Text to AI" (only if text is selected)
        if selected_text:
            send_text_action = QAction("Send Selected Text to AI", self)
            send_text_action.triggered.connect(lambda: self._handle_send_to_ai(selected_text, event.globalPos()))
            menu.addAction(send_text_action)

        menu.addSeparator()

        # 2. "Send Whole Page to AI" (always visible)
        send_page_action = QAction("Send Whole Page to AI", self)
        send_page_action.triggered.connect(lambda: self.full_page_request.emit(event.globalPos()))
        menu.addAction(send_page_action)

        menu.addSeparator()

        # 3. Standard actions to make the menu feel natural
        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(lambda: self.page().triggerAction(QWebEnginePage.Copy))
        menu.addAction(copy_action)

        # Show the menu at the click position
        menu.exec(event.globalPos())

    def _handle_send_to_ai(self, text: str, pos: QPoint) -> None:
        logger.info("BrowserView: emitting ai_request signal with text and pos")
        self.ai_request.emit(text, pos)

    def _on_load_finished(self, ok: bool) -> None:
        if not ok:
            logger.warning("Page failed to load: %s", self.url().toString())

    def navigate_to(self, url_string: str) -> None:
        """Load a fully-resolved URL string (see navigation.resolve_input_to_url)."""
        if url_string == NEW_TAB_URL:
            self.load_new_tab_page()
            return
        self.setUrl(QUrl(url_string))

    def load_new_tab_page(self) -> None:
        from config.settings import get_settings  # local import avoids a cycle at module load time

        settings = get_settings()
        html = build_new_tab_html(settings.search_engine_url, [])
        self.setHtml(html, QUrl(NEW_TAB_URL))
