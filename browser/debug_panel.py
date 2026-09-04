"""
Debug panel shown in the split view when "Debug Mode" is enabled from the
⋮ menu. Displays real AI (Ollama) request/response traffic, and will show
real backend-server traffic once that integration (Phase 4) exists.

This panel never blocks normal browsing — it's a read-only side view.
"""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QPlainTextEdit, QVBoxLayout, QWidget

from browser.debug_log import DebugLog


class DebugPanel(QWidget):
    """Read-only log view of AI and server traffic, for development/inspection."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("debugPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        title = QLabel("Debug: AI & Server Traffic")
        title.setObjectName("debugPanelTitle")
        layout.addWidget(title)

        subtitle = QLabel(
            "Real requests/responses only \u2014 nothing simulated. Server "
            "traffic will appear here once backend submission (Phase 4) "
            "is implemented."
        )
        subtitle.setObjectName("debugPanelSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.log_view = QPlainTextEdit(self)
        self.log_view.setObjectName("debugLogView")
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Consolas", 10))
        layout.addWidget(self.log_view, 1)

        # Backfill anything logged before this panel was created/shown.
        for entry in DebugLog.instance().entries():
            self.log_view.appendPlainText(entry)

        DebugLog.instance().entry_added.connect(self.log_view.appendPlainText)
