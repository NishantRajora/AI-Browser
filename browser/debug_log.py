"""
In-memory debug event log for the "Debug Mode" panel.

Records real AI (Ollama) requests/responses and, once implemented, real
backend-server requests/responses — so the debug panel always shows
actual traffic, never simulated example data. Nothing here sends data
anywhere; it's purely an on-screen record for when Debug Mode is on.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Literal

from PySide6.QtCore import QObject, Signal

Category = Literal["AI", "SERVER"]

_MAX_ENTRIES = 500


class DebugLog(QObject):
    """Process-wide singleton recording debug entries and notifying listeners."""

    entry_added = Signal(str)

    _instance: "DebugLog | None" = None

    def __init__(self) -> None:
        super().__init__()
        self._entries: deque[str] = deque(maxlen=_MAX_ENTRIES)

    @classmethod
    def instance(cls) -> "DebugLog":
        """Return the single shared DebugLog for the process."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def log(self, category: Category, message: str) -> None:
        """Record one entry and notify any connected UI immediately."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] [{category}] {message}"
        self._entries.append(line)
        self.entry_added.emit(line)

    def entries(self) -> list[str]:
        """All entries recorded so far (oldest first), capped at _MAX_ENTRIES."""
        return list(self._entries)
