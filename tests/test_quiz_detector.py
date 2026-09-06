"""
Tests for quiz.detector.

Left as skipped placeholders: quiz/detector.py (the code that would scan
a live page's DOM for question/answer text) is intentionally not
implemented — see README.md for why.
"""

import pytest

pytestmark = pytest.mark.skip(reason="quiz/detector.py is intentionally not implemented.")


def test_detects_question_with_radio_buttons():
    pass


def test_detects_question_with_button_options():
    pass


def test_detects_question_with_labels():
    pass


def test_returns_none_on_invalid_html():
    pass


def test_returns_none_when_no_quiz_present():
    pass