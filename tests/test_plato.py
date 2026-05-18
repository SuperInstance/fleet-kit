"""
tests/test_plato.py — unit tests for fleet_kit.plato.PlatoClient
"""
import hashlib
import hmac
import json
import sys
import unittest
from unittest.mock import patch, MagicMock

# Import directly from the plato module, bypassing __init__.py
example_dir = "/home/ubuntu/.openclaw/workspace/repos/fleet-kit"
sys.path.insert(0, example_dir)

# Load plato.py without triggering package __init__
import importlib.util
spec = importlib.util.spec_from_file_location("plato", f"{example_dir}/fleet_kit/plato.py")
plato_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plato_module)
PlatoClient = plato_module.PlatoClient


class TestPlatoClient(unittest.TestCase):
    """Tests for PlatoClient."""

    def setUp(self):
        """Create a client pointed at a test base URL."""
        self.client = PlatoClient(base_url="http://127.0.0.1:8847", secret="test-secret")

    # ── _sign ─────────────────────────────────────────────────────────────────

    def test_sign_produces_hex_digest(self):
        """_sign should return a hex string of the HMAC-SHA256 digest."""
        result = self.client._sign({"foo": "bar"})
        self.assertIsInstance(result, str)
        self.assertEqual(len(result), 64)  # SHA256 hex = 64 chars

    def test_sign_deterministic(self):
        """_sign should produce the same output for the same input."""
        data = {"question": "What is a ship?", "answer": "A vessel."}
        sig1 = self.client._sign(data)
        sig2 = self.client._sign(data)
        self.assertEqual(sig1, sig2)

    def test_sign_different_secrets_different_output(self):
        """Different secrets should produce different signatures."""
        data = {"question": "x", "answer": "y"}
        client_a = PlatoClient(secret="secret-a")
        client_b = PlatoClient(secret="secret-b")
        self.assertNotEqual(client_a._sign(data), client_b._sign(data))

    # ── status / tile_count ───────────────────────────────────────────────────

    @patch("urllib.request.urlopen")
    def test_status_returns_dict(self, mock_urlopen):
        """status() should return a parsed JSON dict."""
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps({"status": "active", "total_tiles": 42}).encode()
        mock_urlopen.return_value = mock_resp

        result = self.client.status()
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["total_tiles"], 42)

    @patch("urllib.request.urlopen")
    def test_tile_count_returns_total(self, mock_urlopen):
        """tile_count() should return total_tiles from status."""
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps({"total_tiles": 99}).encode()
        mock_urlopen.return_value = mock_resp

        self.assertEqual(self.client.tile_count(), 99)

    @patch("urllib.request.urlopen")
    def test_tile_count_returns_zero_on_error(self, mock_urlopen):
        """tile_count() should return 0 when the server is unreachable."""
        mock_urlopen.side_effect = OSError("connection refused")
        self.assertEqual(self.client.tile_count(), 0)

    # ── submit_tile ───────────────────────────────────────────────────────────

    @patch("urllib.request.urlopen")
    def test_submit_tile_signs_and_posts(self, mock_urlopen):
        """submit_tile should attach a signature and POST to /submit."""
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps({"status": "accepted"}).encode()
        mock_urlopen.return_value = mock_resp

        result = self.client.submit_tile(
            domain="test-room",
            question="What is a lighthouse?",
            answer="A tower with a beacon.",
            tags=["navigation"],
            confidence=0.85,
        )

        # Verify request was a POST with a signed tile
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.get_full_url(), "http://127.0.0.1:8847/submit")
        self.assertEqual(req.method, "POST")

        body = json.loads(req.data)
        self.assertEqual(body["domain"], "test-room")
        self.assertEqual(body["question"], "What is a lighthouse?")
        self.assertEqual(body["answer"], "A tower with a beacon.")
        self.assertEqual(body["tags"], ["navigation"])
        self.assertEqual(body["confidence"], 0.85)
        self.assertEqual(body["agent"], "fleet-kit")
        self.assertIn("signature", body)
        self.assertIn("timestamp", body)

    @patch("urllib.request.urlopen")
    def test_submit_tile_returns_response(self, mock_urlopen):
        """submit_tile should return the parsed server response."""
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps({
            "status": "accepted",
            "room": "test-room",
            "tile_hash": "abc123",
        }).encode()
        mock_urlopen.return_value = mock_resp

        result = self.client.submit_tile("test-room", "Q?", "A.")
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["tile_hash"], "abc123")

    # ── get_room / get_tiles ─────────────────────────────────────────────────

    @patch("urllib.request.urlopen")
    def test_get_room_returns_tiles(self, mock_urlopen):
        """get_room should return room data including tiles."""
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps({
            "tiles": [{"question": "Q1", "answer": "A1"}],
            "tile_count": 1,
        }).encode()
        mock_urlopen.return_value = mock_resp

        room = self.client.get_room("general")
        self.assertEqual(room["tile_count"], 1)
        self.assertEqual(room["tiles"][0]["question"], "Q1")

    @patch("urllib.request.urlopen")
    def test_get_tiles_respects_limit(self, mock_urlopen):
        """get_tiles should return up to `limit` tiles."""
        tiles = [{"question": f"Q{i}", "answer": f"A{i}"} for i in range(5)]
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps({"tiles": tiles, "tile_count": 5}).encode()
        mock_urlopen.return_value = mock_resp

        result = self.client.get_tiles("general", limit=3)
        self.assertEqual(len(result), 3)


if __name__ == "__main__":
    unittest.main()
