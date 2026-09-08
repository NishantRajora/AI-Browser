"""
Settings dialog for MyBrowser.
Allows users to configure general, appearance, browsing, privacy, and AI settings.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QMessageBox, QScrollArea, QWidget, QFrame
)
from PySide6.QtGui import QFont

from config.settings import Settings, get_settings
from ai.ollama import get_ollama_status
from utils.logger import get_logger

logger = get_logger(__name__)

SEARCH_ENGINES = {
    "Google": "https://www.google.com/search?q={query}",
    "Bing": "https://www.bing.com/search?q={query}",
    "DuckDuckGo": "https://duckduckgo.com/?q={query}",
}

class SettingsDialog(QDialog):
    """Dialog for editing MyBrowser settings."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.settings = get_settings()

        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self.setStyleSheet(self._get_style())

        self._build_ui()

    def _get_style(self) -> str:
        return """
        QDialog {
            background-color: #202124;
            color: #e8eaed;
        }
        QLabel {
            color: #9aa0a6;
            font-size: 13px;
        }
        .section-title {
            color: #e8eaed;
            font-size: 16px;
            font-weight: bold;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        QLineEdit, QComboBox {
            background-color: #292a2d;
            border: 1px solid #3c4043;
            border-radius: 4px;
            padding: 6px;
            color: #e8eaed;
            font-size: 13px;
        }
        QLineEdit:focus, QComboBox:focus {
            border: 1px solid #8ab4f8;
        }
        QPushButton {
            background-color: #3c4043;
            color: #e8eaed;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-size: 13px;
        }
        QPushButton:hover {
            background-color: #4f5053;
        }
        QPushButton#saveButton {
            background-color: #8ab4f8;
            color: #202124;
            font-weight: bold;
        }
        QPushButton#saveButton:hover {
            background-color: #aecbfa;
        }
        QPushButton#cancelButton {
            background-color: transparent;
            color: #bdc1c6;
        }
        QPushButton#cancelButton:hover {
            background-color: #3c4043;
        }
        QFrame#sectionDivider {
            background-color: #3c4043;
            max-height: 1px;
        }
        """

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(15)

        # --- General ---
        self._add_section_title(container_layout, "General")

        # Home Page
        self.home_page_edit = self._add_setting_row(container_layout, "Home Page:", QLineEdit(self.settings.home_page))

        # Search Engine
        self.search_engine_combo = QComboBox()
        for name in SEARCH_ENGINES.keys():
            self.search_engine_combo.addItem(name)

        # Set current search engine
        current_engine = next((name for name, url in SEARCH_ENGINES.items() if url == self.settings.search_engine_url), "Google")
        self.search_engine_combo.setCurrentText(current_engine)
        self._add_setting_row(container_layout, "Search Engine:", self.search_engine_combo)

        # Startup
        self.startup_combo = QComboBox()
        self.startup_combo.addItem("Open home page")
        self._add_setting_row(container_layout, "Startup:", self.startup_combo)

        # --- Appearance ---
        self._add_section_title(container_layout, "Appearance")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["System", "Light", "Dark"])
        self.theme_combo.setCurrentText(self.settings.theme)
        self._add_setting_row(container_layout, "Theme:", self.theme_combo)

        # --- Browsing ---
        self._add_section_title(container_layout, "Browsing")
        self.open_links_combo = QComboBox()
        self.open_links_combo.addItem("New tab")
        self.open_links_combo.addItem("Current tab")
        self.open_links_combo.setCurrentIndex(0 if self.settings.open_links_in_new_tab else 1)
        self._add_setting_row(container_layout, "Open links:", self.open_links_combo)

        # --- Privacy ---
        self._add_section_title(container_layout, "Privacy & Data")
        privacy_layout = QHBoxLayout()
        self.btn_clear_data = QPushButton("Clear Browsing Data")
        self.btn_clear_data.clicked.connect(self._on_clear_browsing_data)
        self.btn_clear_history = QPushButton("Clear History")
        self.btn_clear_history.clicked.connect(self._on_clear_history)
        privacy_layout.addWidget(self.btn_clear_data)
        privacy_layout.addWidget(self.btn_clear_history)
        container_layout.addLayout(privacy_layout)

        # --- AI ---
        self._add_section_title(container_layout, "AI Settings")
        self._add_setting_row(container_layout, "Provider:", QLabel("Ollama"))
        self.ollama_url_edit = self._add_setting_row(container_layout, "Ollama URL:", QLineEdit(self.settings.ollama_url))
        self.ollama_model_edit = self._add_setting_row(container_layout, "Model:", QLineEdit(self.settings.ollama_model))

        self.btn_test_ai = QPushButton("Test AI Connection")
        self.btn_test_ai.clicked.connect(self._on_test_ai)
        container_layout.addWidget(self.btn_test_ai)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # --- Bottom Buttons ---
        footer = QHBoxLayout()
        self.btn_reset = QPushButton("Reset to Defaults")
        self.btn_reset.clicked.connect(self._on_reset_defaults)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("cancelButton")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("Save")
        self.btn_save.setObjectName("saveButton")
        self.btn_save.clicked.connect(self.accept)

        footer.addWidget(self.btn_reset)
        footer.addStretch()
        footer.addWidget(self.btn_cancel)
        footer.addWidget(self.btn_save)
        main_layout.addLayout(footer)

    def _add_section_title(self, layout: QVBoxLayout, text: str):
        label = QLabel(text)
        label.setProperty("class", "section-title")
        label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        layout.addWidget(label)

    def _add_setting_row(self, layout: QVBoxLayout, label_text: str, widget: QWidget):
        row = QHBoxLayout()
        label = QLabel(label_text)
        label.setFixedWidth(120)
        row.addWidget(label)
        row.addWidget(widget)
        layout.addLayout(row)
        return widget

    def _on_clear_browsing_data(self) -> None:
        confirm = QMessageBox.question(
            self, "Clear Data",
            "Are you sure you want to clear all cookies and cache? This will sign you out of most websites.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            from browser.profile import get_browser_profile
            profile = get_browser_profile(self.settings)
            profile.clearHttpCache()
            profile.clearAllCookies()
            QMessageBox.information(self, "Success", "Browsing data cleared.")

    def _on_clear_history(self) -> None:
        QMessageBox.information(self, "History", "History clearing is not available yet.")

    def _on_test_ai(self) -> None:
        url = self.ollama_url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Ollama URL cannot be empty.")
            return

        try:
            status = get_ollama_status(url)
            if status.online:
                QMessageBox.information(self, "AI Connection", f"Connection successful!\nFound {len(status.models)} models.")
            else:
                QMessageBox.warning(self, "AI Connection", f"Connection failed: {status.error or 'Unknown error'}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def _on_reset_defaults(self) -> None:
        confirm = QMessageBox.question(
            self, "Reset Defaults",
            "Are you sure you want to reset all settings to their defaults?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            # We can't easily instantiate a 'fresh' Settings without file access
            # so we manually reset known fields.
            self.settings.home_page = "https://www.google.com"
            self.settings.search_engine_url = SEARCH_ENGINES["Google"]
            self.settings.theme = "System"
            self.settings.open_links_in_new_tab = True
            self.settings.ollama_url = "http://localhost:11434"
            self.settings.ollama_model = "qwen2.5"

            # Update UI
            self.home_page_edit.setText(self.settings.home_page)
            self.search_engine_combo.setCurrentText("Google")
            self.theme_combo.setCurrentText("System")
            self.open_links_combo.setCurrentIndex(0)
            self.ollama_url_edit.setText(self.settings.ollama_url)
            self.ollama_model_edit.setText(self.settings.ollama_model)

            QMessageBox.information(self, "Reset", "Settings have been reset to defaults.")

    def get_updated_settings(self) -> dict:
        """Collect current values from UI to update the settings object."""
        return {
            "home_page": self.home_page_edit.text(),
            "search_engine_url": SEARCH_ENGINES.get(self.search_engine_combo.currentText(), SEARCH_ENGINES["Google"]),
            "theme": self.theme_combo.currentText(),
            "open_links_in_new_tab": self.open_links_combo.currentIndex() == 0,
            "ollama_url": self.ollama_url_edit.text(),
            "ollama_model": self.ollama_model_edit.text(),
        }
