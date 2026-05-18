"""
Tests for fleet_kit.models — mock HTTP, don't hit real APIs.
"""
import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Import models module directly to bypass fleet_kit/__init__.py
# (which imports uncreated sub-modules)
_MODELS_FILE = os.path.join(os.path.dirname(__file__), "..", "fleet_kit", "models.py")
import importlib.util
spec = importlib.util.spec_from_file_location("fleet_kit_models", _MODELS_FILE)
fleet_kit_models = importlib.util.module_from_spec(spec)
sys.modules["fleet_kit_models"] = fleet_kit_models
spec.loader.exec_module(fleet_kit_models)

FleetModelClient = fleet_kit_models.FleetModelClient
ModelResponse = fleet_kit_models.ModelResponse


# ── Shared mock response body ──────────────────────────────────────────────────

MOCK_BODY = json.dumps({
    "choices": [{"message": {"content": "hello world"}}],
    "usage": {"prompt_tokens": 5, "completion_tokens": 2},
}).encode()


# ── Helper: mock context-manager response ─────────────────────────────────────

def _mock_response(body_bytes: bytes):
    mock_resp = MagicMock()
    mock_resp.read = MagicMock(return_value=body_bytes)
    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_resp)
    mock_cm.__exit__ = MagicMock(return_value=False)
    return mock_cm


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """Fresh client per test, no real keys needed."""
    return FleetModelClient()


# ── ModelResponse tests ────────────────────────────────────────────────────────

def test_model_response_defaults():
    r = ModelResponse(text="hello")
    assert r.text == "hello"
    assert r.model == ""
    assert r.tokens_in == 0
    assert r.tokens_out == 0


def test_model_response_full():
    r = ModelResponse(text="answer", model="test-model", tokens_in=10, tokens_out=5)
    assert r.text == "answer"
    assert r.model == "test-model"
    assert r.tokens_in == 10
    assert r.tokens_out == 5


# ── FleetModelClient.ask tests ────────────────────────────────────────────────
#
# Mode routing:
#   creative (localhost:9438, http)  → urlopen directly
#   fast     (siliconflow, https)   → build_opener().open()
#   deep     (z.ai, https)          → build_opener().open()

def test_ask_fast_mode(client):
    """fast mode hits SiliconFlow via build_opener with Bearer auth header."""
    mock_opener = MagicMock()
    mock_opener.open.return_value = _mock_response(MOCK_BODY)
    with patch("urllib.request.build_opener", return_value=mock_opener):
        resp = client.ask("say hello", mode="fast")

        assert resp.text == "hello world"
        assert resp.model == "deepseek-ai/DeepSeek-V3"
        assert resp.tokens_in == 5
        assert resp.tokens_out == 2
        mock_opener.open.assert_called_once()
        call = mock_opener.open.call_args
        req = call[0][0]
        assert "siliconflow.com" in req.full_url
        assert "Bearer" in dict(req.headers).get("Authorization", "")


def test_ask_creative_mode(client):
    """creative mode hits local MCP at localhost:9438 with no auth header."""
    with patch("urllib.request.urlopen", return_value=_mock_response(MOCK_BODY)) as mock_urlopen:
        resp = client.ask("brainstorm", mode="creative")

        assert resp.text == "hello world"
        assert resp.model == "ByteDance/Seed-2.0-mini"
        mock_urlopen.assert_called_once()
        call = mock_urlopen.call_args
        req = call[0][0]
        assert "localhost:9438" in req.full_url
        # local MCP should NOT have Authorization header
        assert "Authorization" not in dict(req.headers)


def test_ask_deep_mode(client):
    """deep mode hits z.ai via build_opener with SSL context."""
    mock_opener = MagicMock()
    mock_opener.open.return_value = _mock_response(MOCK_BODY)
    with patch("urllib.request.build_opener", return_value=mock_opener):
        resp = client.ask("reason deeply", mode="deep")

        assert resp.text == "hello world"
        assert resp.model == "glm-5.1"
        mock_opener.open.assert_called_once()


def test_ask_parallel(client):
    """ask_parallel returns one ModelResponse per prompt in sequence."""
    mock_opener = MagicMock()
    mock_opener.open.return_value = _mock_response(MOCK_BODY)
    with patch("urllib.request.build_opener", return_value=mock_opener):
        resps = client.ask_parallel(["ask 1", "ask 2"], mode="fast")

        assert len(resps) == 2
        assert all(isinstance(r, ModelResponse) for r in resps)
        assert mock_opener.open.call_count == 2


def test_ask_invalid_mode(client):
    """Invalid mode raises ValueError."""
    with pytest.raises(ValueError, match="Unknown mode"):
        client.ask("hello", mode="invalid")