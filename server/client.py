"""
Minimal backend HTTP client.

Design rules (per project spec):
  * The browser is never dependent on the backend for normal browsing.
  * If the server is unreachable, requests fail silently (logged, not
    raised) and the app keeps working exactly as if the feature were off.
  * No page content is ever sent wholesale — only the specific, small
    payloads defined in server/models.py, and only when the caller
    explicitly asks (nothing runs in the background automatically).
"""

from __future__ import annotations

from dataclasses import dataclass

import requests

from server.models import SummaryRecord
from utils.logger import get_logger

logger = get_logger(__name__)

_REQUEST_TIMEOUT_SECONDS = 5.0


@dataclass
class BackendResult:
    """Outcome of a single backend call. Never an exception."""

    success: bool
    error: str | None = None


class BackendClient:
    """Thin wrapper around a configurable backend base URL."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def send_summary(self, record: SummaryRecord) -> BackendResult:
        """
        POST a SummaryRecord to {base_url}/summaries.

        Never raises. Returns BackendResult(success=False, error=...) on
        any connection error, timeout, or non-2xx response — callers
        should treat that as "couldn't save it this time", not a crash.
        """
        url = f"{self._base_url}/summaries"
        try:
            response = requests.post(url, json=record.to_dict(), timeout=_REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            logger.info("Sent summary for %s to backend.", record.page_url)
            return BackendResult(success=True)

        except requests.exceptions.ConnectionError:
            logger.info("Backend not reachable at %s; continuing without it.", self._base_url)
            return BackendResult(success=False, error="Server is not reachable")

        except requests.exceptions.Timeout:
            logger.warning("Backend request timed out at %s.", self._base_url)
            return BackendResult(success=False, error="Server request timed out")

        except requests.exceptions.RequestException as exc:
            logger.warning("Backend request failed: %s", exc)
            return BackendResult(success=False, error="Server request failed")