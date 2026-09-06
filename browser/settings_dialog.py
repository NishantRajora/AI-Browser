"""
Settings dialog for MyBrowser.
Allows users to edit app configuration and persist it to disk.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QPushButton,
    QVBoxLayout,
    QDialogButtonBox,
    QWidget
)
from PySide6.QtCore import Qt

from config.settings import Settings, get_settings

class SettingsDialog(QDialog):
    """Dialog for editing application settings."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._settings = get_settings()

        self.setWindowTitle("Settings")
        self.setMinimumWidth(450)
        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Form layout for settings fields
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setSpacing(10)

        # Browsing Settings
        self.home_page_edit = QLineEdit(self._settings.home_page)
        form.addRow("Home Page:", self.home_page_edit)

        self.search_engine_edit = QLineEdit(self._settings.search_engine_url)
        form.addRow("Search Engine URL:", self.search_engine_edit)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(400, 5000)
        self.width_spin.setValue(self._settings.window_width)
        form.addRow("Window Width:", self.width_spin)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(300, 5000)
        self.height_spin.setValue(self._settings.window_height)
        form.addRow("Window Height:", self.height_spin)

        main_layout.addLayout(form)

        # AI / Backend Settings
        main_layout.addWidget(QWidget()) # Spacer

        # Simple label for section
        from PySide6.QtWidgets import QLabel
        section_label = QLabel("AI & Backend Connectivity")
        section_label.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 10px;")
        main_layout.addWidget(section_label)

        ai_form = QFormLayout()
        ai_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        ai_form.setSpacing(10)

        self.ollama_url_edit = QLineEdit(self._settings.ollama_url)
        ai_form.addRow("Ollama URL:", self.ollama_url_edit)

        self.ollama_model_edit = QLineEdit(self._settings.ollama_model)
        ai_form.addRow("Default Model:", self.ollama_model_edit)

        self.backend_url_edit = QLineEdit(self._settings.backend_url)
        ai_form.addRow("Backend URL:", self.backend_url_edit)

        main_layout.addLayout(ai_form)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

    def get_updated_settings(self) -> dict:
        """Return a dictionary of updated settings values."""
        return {
            "home_page": self.home_page_edit.text(),
            "search_engine_url": self.search_engine_edit.text(),
            "window_width": self.width_spin.value(),
            "window_height": self.height_spin.value(),
            "ollama_url": self.ollama_url_edit.text(),
            "ollama_model": self.ollama_model_edit.text(),
            "backend_url": self.backend_url_edit.text(),
        }

    def save_settings(self) -> None:
        """Apply the updates to the global settings singleton and save to disk."""
        updates = self.get_updated_settings()
        for key, value in updates.items():
            setattr(self._settings, key, value)
        self._settings.save()
