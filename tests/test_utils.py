"""
Tests for fleet_kit.utils — credential loading, signing, HTTP helpers, fs utils.
"""
import json
import os
import tempfile
from pathlib import Path

import pytest

from fleet_kit.utils import ensure_dir, json_get, json_post, load_key, sign_data


# ── load_key ───────────────────────────────────────────────────────────────────

def test_load_key_from_env(monkeypatch):
    """Environment variable is preferred."""
    monkeypatch.setenv("MY_TEST_KEY", "secret123")
    assert load_key("MY_TEST_KEY") == "secret123"


def test_load_key_from_vault(tmp_path, monkeypatch):
    """Falls back to ~/.credentials_vault when env var is absent."""
    monkeypatch.delenv("MY_TEST_KEY", raising=False)
    vault = tmp_path / ".credentials_vault"
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    vault.write_text("MY_TEST_KEY=from_vault\nOTHER_KEY=ignore\n")
    assert load_key("MY_TEST_KEY") == "from_vault"


def test_load_key_missing_returns_empty(monkeypatch):
    """Unknown key returns empty string."""
    monkeypatch.delenv("DEFINITELY_NOT_HERE", raising=False)
    monkeypatch.setattr(Path, "home", lambda: Path("/nonexistent"))
    assert load_key("DEFINITELY_NOT_HERE") == ""


# ── sign_data ───────────────────────────────────────────────────────────────────

def test_sign_data_deterministic():
    """Same dict + secret always produces the same hex signature."""
    data = {"b": 2, "a": 1}
    sig1 = sign_data(data, "hunter2")
    sig2 = sign_data(data, "hunter2")
    assert sig1 == sig2


def test_sign_data_sort_keys():
    """Key ordering is canonicalized (sort_keys=True)."""
    swap = {"a": 1, "b": 2}
    reverse = {"b": 2, "a": 1}
    assert sign_data(swap, "sec") == sign_data(reverse, "sec")


def test_sign_data_different_secrets_differ():
    """Different secrets produce different signatures."""
    data = {"x": 9}
    assert sign_data(data, "left") != sign_data(data, "right")


# ── json_get ───────────────────────────────────────────────────────────────────

def test_json_get_invalid_url():
    """Bad URL returns an error dict."""
    result = json_get("http://localhost:1-nonexistent/", timeout=2)
    assert "error" in result


def test_json_get_valid_url(httpserver):
    """Good URL returns parsed JSON."""
    httpserver.add_handler(
        httpserver.expect_request("/ok").respond_with_json({"status": "ok"})
    )
    result = json_get(httpserver.url + "/ok", timeout=5)
    assert result == {"status": "ok"}


# ── json_post ─────────────────────────────────────────────────────────────────

def test_json_post_invalid_url():
    """Posting to a dead URL returns an error dict."""
    result = json_post("http://localhost:1-nonexistent/", {"foo": "bar"}, timeout=2)
    assert "error" in result


def test_json_post_success(httpserver):
    """POSTing JSON returns parsed response."""
    httpserver.add_handler(
        httpserver.expect_request("/post", method="POST").respond_with_json(
            {"received": True}
        )
    )
    result = json_post(httpserver.url + "/post", {"received": True}, timeout=5)
    assert result == {"received": True}


# ── ensure_dir ─────────────────────────────────────────────────────────────────

def test_ensure_dir_creates_nested(tmp_path):
    """Creates leaf plus all missing parent directories."""
    target = tmp_path / "a" / "b" / "c"
    returned = ensure_dir(str(target))
    assert target.is_dir()
    assert returned == str(target)


def test_ensure_dir_idempotent(tmp_path):
    """Calling twice on an existing directory does not raise."""
    target = tmp_path / "exists"
    target.mkdir()
    ensure_dir(str(target))  # must not raise


def test_ensure_dir_returns_path(tmp_path):
    """Returns exactly the path that was passed in."""
    p = str(tmp_path / "my_dir")
    assert ensure_dir(p) == p