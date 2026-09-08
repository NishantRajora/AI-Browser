"""
Centralized application settings.

Settings are persisted as JSON in the user's local app-data directory so the
browser remembers configuration between runs. No secrets or credentials are
stored here. All values have sane defaults so the app runs correctly even if
the settings file does not exist yet.

Phase 1 only uses HOME_PAGE / SEARCH_ENGINE / window geometry. The
ollama/backend/quiz fields exist now so the schema does not need to change
later, but they are inert until Phase 2/3 wire them up.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from utils.logger import get_logger

logger = get_logger(__name__)

APP_NAME = "MyBrowser"
NEW_TAB_URL = "mybrowser://newtab"


def _default_config_dir() -> Path:
    """Return an OS-appropriate directory for storing app configuration."""
    if os.name == "nt":
        base = os.environ.get("APPDATA", str(Path.home()))
    else:
        base = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(base) / APP_NAME


@dataclass
class Settings:
    """All user-configurable settings for MyBrowser."""

    # Browsing
    home_page: str = "https://www.google.com"
    search_engine_url: str = "https://www.google.com/search?q={query}"
    window_width: int = 1400
    window_height: int = 900

    # AI / quiz (used starting Phase 2/3; harmless if unused)
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5"
    backend_url: str = "http://localhost:8000"
    ai_confidence_threshold: float = 0.90
    quiz_detection_enabled: bool = False
    full_page_scan_enabled: bool = False

    _config_path: Path = field(default_factory=lambda: _default_config_dir() / "settings.json", repr=False)

    @classmethod
    def load(cls, config_path: Path | None = None) -> "Settings":
        """Load settings from disk, falling back to defaults on any error."""
        path = config_path or (_default_config_dir() / "settings.json")
        settings = cls(_config_path=path)
        if not path.exists():
            logger.info("No settings file found at %s, using defaults.", path)
            return settings

        try:
            data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            for key, value in data.items():
                if hasattr(settings, key) and not key.startswith("_"):
                    setattr(settings, key, value)
            logger.info("Loaded settings from %s", path)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read settings (%s); using defaults.", exc)

        return settings

    def save(self) -> None:
        """Persist settings to disk. Never raises; logs on failure."""
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            data = {k: v for k, v in asdict(self).items() if not k.startswith("_")}
            self._config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.info("Settings saved to %s", self._config_path)
        except OSError as exc:
            logger.error("Failed to save settings: %s", exc)

    def profile_storage_path(self) -> Path:
        """Directory used for the persistent QWebEngineProfile (cookies/cache)."""
        return _default_config_dir() / "profile"


# A single process-wide settings instance, loaded lazily.
_settings_instance: Settings | None = None


def get_settings() -> Settings:
    """Return the shared Settings instance, loading it on first access."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings.load()
    return _settings_instance
