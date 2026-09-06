"""
Tests for ai.ollama — fully mocked, no real Ollama instance required and
no network access used.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests  # noqa: E402

from ai.ollama import generate_completion, get_ollama_status  # noqa: E402

BASE_URL = "http://localhost:11434"


def _make_response(json_data=None, raise_for_status_error=None):
    response = MagicMock()
    if raise_for_status_error:
        response.raise_for_status.side_effect = raise_for_status_error
    else:
        response.raise_for_status.return_value = None
    response.json.return_value = json_data or {}
    return response


# -- get_ollama_status ---------------------------------------------------

@patch("ai.ollama.requests.get")
def test_valid_response_reports_online_with_models(mock_get):
    mock_get.return_value = _make_response({"models": [{"name": "qwen2.5"}, {"name": "llama3.2"}]})
    status = get_ollama_status(BASE_URL)
    assert status.online is True
    assert status.models == ["qwen2.5", "llama3.2"]
    assert status.error is None


@patch("ai.ollama.requests.get")
def test_response_with_no_models_key_is_still_online_with_empty_list(mock_get):
    mock_get.return_value = _make_response({})
    status = get_ollama_status(BASE_URL)
    assert status.online is True
    assert status.models == []


@patch("ai.ollama.requests.get")
def test_malformed_json_is_reported_as_offline(mock_get):
    response = _make_response()
    response.json.side_effect = ValueError("not JSON")
    mock_get.return_value = response
    status = get_ollama_status(BASE_URL)
    assert status.online is False
    assert status.error is not None


@patch("ai.ollama.requests.get")
def test_connection_error_is_reported_as_offline(mock_get):
    mock_get.side_effect = requests.exceptions.ConnectionError("refused")
    status = get_ollama_status(BASE_URL)
    assert status.online is False
    assert status.error == "Not running"


@patch("ai.ollama.requests.get")
def test_timeout_is_reported_as_offline(mock_get):
    mock_get.side_effect = requests.exceptions.Timeout("timed out")
    status = get_ollama_status(BASE_URL)
    assert status.online is False
    assert status.error == "Connection timed out"


@patch("ai.ollama.requests.get")
def test_http_error_status_is_reported_as_offline(mock_get):
    mock_get.return_value = _make_response(raise_for_status_error=requests.exceptions.HTTPError("500"))
    status = get_ollama_status(BASE_URL)
    assert status.online is False
    assert status.error is not None


# -- generate_completion --------------------------------------------------

@patch("ai.ollama.requests.post")
def test_generate_returns_text_on_success(mock_post):
    mock_post.return_value = _make_response({"response": "This page is about..."})
    result = generate_completion(BASE_URL, "qwen2.5", "summarize this")
    assert result.success is True
    assert result.text == "This page is about..."


def test_generate_with_no_model_selected_fails_fast():
    result = generate_completion(BASE_URL, "", "summarize this")
    assert result.success is False
    assert "model" in (result.error or "").lower()


@patch("ai.ollama.requests.post")
def test_generate_with_empty_response_is_treated_as_failure(mock_post):
    mock_post.return_value = _make_response({"response": ""})
    result = generate_completion(BASE_URL, "qwen2.5", "summarize this")
    assert result.success is False


@patch("ai.ollama.requests.post")
def test_generate_connection_error_is_handled(mock_post):
    mock_post.side_effect = requests.exceptions.ConnectionError("refused")
    result = generate_completion(BASE_URL, "qwen2.5", "summarize this")
    assert result.success is False
    assert result.error == "Ollama is not running"


@patch("ai.ollama.requests.post")
def test_generate_timeout_is_handled(mock_post):
    mock_post.side_effect = requests.exceptions.Timeout("timed out")
    result = generate_completion(BASE_URL, "qwen2.5", "summarize this")
    assert result.success is False
    assert result.error == "Request timed out"