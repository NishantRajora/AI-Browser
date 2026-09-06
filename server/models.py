"""
Request schema(s) sent to the backend.

Currently just one: a record of an AI Assistant page summary. This is
intentionally NOT a quiz-answer submission schema — see README.md for
why quiz detection/answering isn't implemented.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class SummaryRecord:
    """One page-summarization event, as sent to the backend (if enabled)."""

    page_url: str
    page_title: str
    summary: str
    model: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self) -> None:
        if not self.page_url:
            raise ValueError("SummaryRecord requires a page_url.")
        if not self.summary.strip():
            raise ValueError("SummaryRecord requires a non-empty summary.")

    def to_dict(self) -> dict:
        return asdict(self)