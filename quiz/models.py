"""
Data model for a single detected quiz-style question.

This module only defines a plain data structure. It is not, by itself,
capable of finding questions on a page or answering them — see
quiz/detector.py and ai/verifier.py for why those remain unimplemented.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class QuizQuestion:
    """A single multiple-choice-style question found on a page."""

    question: str
    options: list[str]

    question_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    page_url: str = ""
    page_title: str = ""
    detected_at: datetime = field(default_factory=datetime.now)
    confidence: float = 0.0  # heuristic confidence the detector had, 0.0-1.0

    def __post_init__(self) -> None:
        if not self.question.strip():
            raise ValueError("QuizQuestion requires a non-empty question.")
        if len(self.options) < 2:
            raise ValueError("QuizQuestion requires at least 2 options.")