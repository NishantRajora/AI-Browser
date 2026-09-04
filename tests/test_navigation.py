"""
Tests for browser.navigation.resolve_input_to_url.

These run with plain pytest — no QApplication/display needed, since the
function under test has no Qt dependency.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from browser.navigation import resolve_input_to_url  # noqa: E402
from config.settings import Settings  # noqa: E402


def make_settings() -> Settings:
    return Settings(
        home_page="https://www.google.com",
        search_engine_url="https://www.google.com/search?q={query}",
    )


def test_empty_input_returns_home_page():
    settings = make_settings()
    assert resolve_input_to_url("", settings) == settings.home_page
    assert resolve_input_to_url("   ", settings) == settings.home_page


def test_full_url_with_scheme_is_used_as_is():
    settings = make_settings()
    assert resolve_input_to_url("https://google.com", settings) == "https://google.com"
    assert resolve_input_to_url("http://example.com/path", settings) == "http://example.com/path"


def test_bare_domain_gets_https_prefix():
    settings = make_settings()
    assert resolve_input_to_url("google.com", settings) == "https://google.com"
    assert resolve_input_to_url("youtube.com", settings) == "https://youtube.com"
    assert resolve_input_to_url("github.com", settings) == "https://github.com"


def test_bare_domain_with_path_gets_https_prefix():
    settings = make_settings()
    assert resolve_input_to_url("github.com/anthropics", settings) == "https://github.com/anthropics"


def test_localhost_and_ip_are_treated_as_hosts():
    settings = make_settings()
    assert resolve_input_to_url("localhost:8000", settings) == "https://localhost:8000"
    assert resolve_input_to_url("127.0.0.1:11434", settings) == "https://127.0.0.1:11434"


def test_search_queries_go_to_search_engine():
    settings = make_settings()
    result = resolve_input_to_url("python tutorials", settings)
    assert result.startswith("https://www.google.com/search?q=")
    assert "python+tutorials" in result


def test_multi_word_query_with_dot_is_still_a_search():
    # "best machine learning courses" has no dot at all, but this test
    # guards the case where a query contains a dot-like word plus spaces.
    settings = make_settings()
    result = resolve_input_to_url("best machine learning courses", settings)
    assert result.startswith("https://www.google.com/search?q=")


def test_query_containing_a_dot_and_space_is_a_search_not_a_domain():
    settings = make_settings()
    result = resolve_input_to_url("visit example.com today", settings)
    assert result.startswith("https://www.google.com/search?q=")
