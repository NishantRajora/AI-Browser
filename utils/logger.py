"""
Central logging configuration for MyBrowser.

Guidelines enforced by convention throughout the codebase (see project docs):
  * Never log passwords, cookies, auth tokens, or full page content.
  * Log operational events: startup, navigation errors, AI/service connectivity,
    quiz-detection outcomes (counts/booleans, not full answer content beyond
    what the user already sees on screen).

Usage:
    from utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Something happened")
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_CONFIGURED = False


def _log_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA", str(Path.home()))
    else:
        base = os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state"))
    path = Path(base) / "MyBrowser" / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _configure_root_logger() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger("mybrowser")
    root.setLevel(logging.INFO)

    formatter = logging.Formatter(_LOG_FORMAT)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    try:
        file_handler = RotatingFileHandler(
            _log_dir() / "mybrowser.log",
            maxBytes=2 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError:
        # Logging to a file is best-effort; console logging still works.
        root.warning("Could not open log file; continuing with console logging only.")

    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger under the shared 'mybrowser' hierarchy."""
    _configure_root_logger()
    return logging.getLogger(f"mybrowser.{name}")
