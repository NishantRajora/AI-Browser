"""Data model for a detected on-page question.

This is the one piece of Phase 2 defined now, since detector.py and
parser.py both need a shared shape to target. Nothing constructs a
QuizQuestion yet -- that starts once quiz/detector.py and quiz/parser.py
are implemented.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class QuizQuestion:
    question_text: str
    options: list[str] = field(default_factory=list)
    source_url: str = ""
    element_selector: str = ""  # how it was located in the DOM, for debugging