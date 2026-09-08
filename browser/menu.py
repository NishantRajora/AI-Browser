"""
The "\u22ee" (more options) toolbar button and its dropdown menu.

Contains:
  * A live Ollama online/offline status row + installed model count.
  * A submenu to pick which installed Ollama model to use.
  * A toggle to turn AI review of quiz data off entirely (nothing is sent
    to Ollama when off; a future backend integration would instead send
    detected quiz data straight to the server per this same flag).

The Ollama status check is a blocking HTTP call (see ai/ollama.py), so it
runs on a background QThread here and never freezes the UI.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QLabel, QMenu, QToolButton, QWidget, QWidgetAction

from ai.ollama import OllamaStatus, get_ollama_status
from browser.debug_log import DebugLog
from config.settings import Settings
from utils.logger import get_logger

logger = get_logger(__name__)

_STATUS_STYLE_CHECKING = "padding: 6px 14px; color: #9aa0a6;"
_STATUS_STYLE_ONLINE = "padding: 6px 14px; color: #4caf50;"
_STATUS_STYLE_OFFLINE = "padding: 6px 14px; color: #e05252;"


class _OllamaStatusWorker(QThread):
    """Runs the blocking Ollama status check off the UI thread."""

    finished_status = Signal(object)  # emits an OllamaStatus

    def __init__(self, base_url: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._base_url = base_url

    def run(self) -> None:  # noqa: D102 (Qt override, no docstring needed)
        self.finished_status.emit(get_ollama_status(self._base_url))


class MoreOptionsButton(QToolButton):
    """The '\u22ee' toolbar button that opens the settings menu."""

    debug_mode_toggled = Signal(bool)
    settings_requested = Signal()

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._worker: _OllamaStatusWorker | None = None

        self.setObjectName("navButton")
        self.setText("\u22ee")
        self.setToolTip("Settings")
        self.setFixedSize(34, 34)
        self.setPopupMode(QToolButton.InstantPopup)

        self.menu = QMenu(self)
        self.setMenu(self.menu)
        self.menu.aboutToShow.connect(self._refresh_ollama_status)

        self._model_action_group = QActionGroup(self.menu)
        self._model_action_group.setExclusive(True)

        self._build_menu_items()

    # -- Menu construction ----------------------------------------------------

    def _build_menu_items(self) -> None:
        self._status_action = QWidgetAction(self.menu)
        self._status_label = QLabel("Ollama: checking\u2026")
        self._status_label.setStyleSheet(_STATUS_STYLE_CHECKING)
        self._status_action.setDefaultWidget(self._status_label)
        self.menu.addAction(self._status_action)

        self._model_menu = self.menu.addMenu("Ollama Model")
        self._populate_model_menu([])  # filled in once the first status check returns

        self.menu.addSeparator()

        self._debug_mode_action = QAction("Debug Mode", self.menu)
        self._debug_mode_action.setCheckable(True)
        self._debug_mode_action.setChecked(False)
        self._debug_mode_action.setToolTip(
            "Split the window to show real AI and server request/response traffic."
        )
        self._debug_mode_action.toggled.connect(self.debug_mode_toggled.emit)
        self.menu.addAction(self._debug_mode_action)

        self.menu.addSeparator()

        settings_action = QAction("Settings\u2026", self.menu)
        settings_action.triggered.connect(self.settings_requested.emit)
        self.menu.addAction(settings_action)

    def _populate_model_menu(self, models: list[str]) -> None:
        self._model_menu.clear()
        for action in list(self._model_action_group.actions()):
            self._model_action_group.removeAction(action)

        if not models:
            placeholder = QAction("No models found", self._model_menu)
            placeholder.setEnabled(False)
            self._model_menu.addAction(placeholder)
            return

        for model_name in models:
            action = QAction(model_name, self._model_menu)
            action.setCheckable(True)
            action.setChecked(model_name == self._settings.ollama_model)
            action.triggered.connect(lambda _checked, name=model_name: self._on_model_selected(name))
            self._model_action_group.addAction(action)
            self._model_menu.addAction(action)

    # -- Handlers ---------------------------------------------------------------

    def _on_model_selected(self, model_name: str) -> None:
        self._settings.ollama_model = model_name
        self._settings.save()
        logger.info("Ollama model set to '%s'", model_name)

    def _on_full_page_scan_toggled(self, checked: bool) -> None:
        """Persist full‑page‑scan setting to disk."""
        self._settings.full_page_scan_enabled = checked
        self._settings.save()
        logger.info("Full Page Scan %s", "enabled" if checked else "disabled")

    def _refresh_ollama_status(self) -> None:
        self._status_label.setText("Ollama: checking\u2026")
        self._status_label.setStyleSheet(_STATUS_STYLE_CHECKING)

        if self._worker is not None and self._worker.isRunning():
            return  # a check is already in flight; let it finish

        self._worker = _OllamaStatusWorker(self._settings.ollama_url, self)
        self._worker.finished_status.connect(self._on_status_ready)
        DebugLog.instance().log("STATUS", f"Request -> GET {self._settings.ollama_url}/api/tags")
        self._worker.start()

    def _on_status_ready(self, status: OllamaStatus) -> None:
        if status.online:
            count = len(status.models)
            model_word = "model" if count == 1 else "models"
            self._status_label.setText(f"\u25cf Ollama: Online ({count} {model_word})")
            self._status_label.setStyleSheet(_STATUS_STYLE_ONLINE)
            models_list = ", ".join(status.models) if status.models else "none"
            DebugLog.instance().log("STATUS", f"Response <- 200 OK, models: [{models_list}]")
        else:
            reason = status.error or "Offline"
            self._status_label.setText(f"\u25cf Ollama: {reason}")
            self._status_label.setStyleSheet(_STATUS_STYLE_OFFLINE)
            DebugLog.instance().log("STATUS", f"Response <- error: {reason}")

        self._populate_model_menu(status.models)
