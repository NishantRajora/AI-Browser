"""
Persistent Chromium (QWebEngineProfile) management.

Isolated here so the rest of the app never touches QWebEngineProfile
directly. Using a persistent, named profile means cookies, local storage,
and HTTP cache survive between application runs, like a normal browser.
"""

from __future__ import annotations

from PySide6.QtWebEngineCore import QWebEngineProfile

from config.settings import Settings
from utils.logger import get_logger

logger = get_logger(__name__)

_profile_instance: QWebEngineProfile | None = None


def get_browser_profile(settings: Settings) -> QWebEngineProfile:
    """
    Return the single shared, persistent QWebEngineProfile for the app.

    All tabs/webviews should use this same profile so they share cookies
    and cache the way tabs in a real browser do.
    """
    global _profile_instance
    if _profile_instance is not None:
        return _profile_instance

    storage_path = settings.profile_storage_path()
    storage_path.mkdir(parents=True, exist_ok=True)

    profile = QWebEngineProfile("MyBrowserProfile")
    profile.setPersistentStoragePath(str(storage_path))
    profile.setCachePath(str(storage_path / "cache"))
    profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
    profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)

    logger.info("Initialized persistent browser profile at %s", storage_path)
    _profile_instance = profile
    return profile
