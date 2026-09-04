"""
MyBrowser entry point.

Phase 1: browser window, tabs, navigation, Chromium rendering via
QtWebEngine. AI/quiz features are not wired in yet (see ai/, quiz/, server/
for their Phase 2+ stubs).
"""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

# QtWebEngine must be able to see high-DPI/GL attributes before QApplication
# is constructed; QtWebEngineWidgets sets these up on import.
from PySide6 import QtWebEngineWidgets  # noqa: F401  (import needed for side effects)

from browser.window import MainWindow
from config.settings import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)


def main() -> int:
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    app = QApplication(sys.argv)
    app.setApplicationName("MyBrowser")
    app.setOrganizationName("MyBrowser")

    logger.info("MyBrowser starting up.")
    settings = get_settings()

    window = MainWindow(settings)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
