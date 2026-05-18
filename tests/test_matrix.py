"""
Tests for fleet_kit.matrix.MatrixClient.
Uses unittest.mock to mock HTTP calls; no network required.
"""
import json
import sys
import unittest
from unittest.mock import MagicMock, patch

# Import directly from the plato module, bypassing __init__.py
example_dir = "/home/ubuntu/.openclaw/workspace/repos/fleet-kit"
sys.path.insert(0, example_dir)

# Load matrix.py without triggering package __init__ (which imports unavailable modules)
import importlib.util
spec = importlib.util.spec_from_file_location("matrix", f"{example_dir}/fleet_kit/matrix.py")
matrix_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(matrix_module)
MatrixClient = matrix_module.MatrixClient


class TestMatrixClient(unittest.TestCase):
    """Test MatrixClient methods with mocked HTTP responses."""

    def _client(self, token: str = "test-token"):
        return MatrixClient(base_url="http://127.0.0.1:6167", token=token)

    # ------------------------------------------------------------------
    # status
    # ------------------------------------------------------------------

    @patch("urllib.request.urlopen")
    def test_status_returns_version_info(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value.read.return_value = b'{"versions": ["v1.1"]}'
        result = self._client().status()
        self.assertEqual(result, {"versions": ["v1.1"]})

    # ------------------------------------------------------------------
    # send_room
    # ------------------------------------------------------------------

    @patch("urllib.request.urlopen")
    def test_send_room_returns_event_id(self, mock_urlopen):
        mock_resp = {"event_id": "$abc123"}
        mock_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(mock_resp).encode()
        result = self._client().send_room("!roomId:server", "hello fleet")
        self.assertEqual(result["event_id"], "$abc123")

    @patch("urllib.request.urlopen")
    def test_send_room_builds_correct_url(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value.read.return_value = b'{"event_id": "$xyz"}'
        self._client().send_room("!myroom:example.com", "test message")
        call_args = mock_urlopen.call_args
        url: urllib.request.Request = call_args[0][0]
        self.assertIn("!myroom:example.com", url.full_url)
        self.assertIn("send/m.room.message", url.full_url)

    # ------------------------------------------------------------------
    # get_messages
    # ------------------------------------------------------------------

    @patch("urllib.request.urlopen")
    def test_get_messages_returns_chunk(self, mock_urlopen):
        events = [{"type": "m.room.message", "body": "hi"}]
        mock_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps({"chunk": events}).encode()
        result = self._client().get_messages("!room1:host", limit=10)
        self.assertEqual(result, events)

    @patch("urllib.request.urlopen")
    def test_get_messages_default_limit(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value.read.return_value = b'{"chunk": []}'
        self._client().get_messages("!room1:host")
        url: urllib.request.Request = mock_urlopen.call_args[0][0]
        self.assertIn("limit=20", url.full_url)

    # ------------------------------------------------------------------
    # list_rooms
    # ------------------------------------------------------------------

    @patch("urllib.request.urlopen")
    def test_list_rooms_returns_list(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(["!room1", "!room2"]).encode()
        result = self._client().list_rooms()
        self.assertEqual(result, ["!room1", "!room2"])

    # ------------------------------------------------------------------
    # create_room
    # ------------------------------------------------------------------

    @patch("urllib.request.urlopen")
    def test_create_room_returns_room_id(self, mock_urlopen):
        mock_resp = {"room_id": "!newroom:example.com"}
        mock_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(mock_resp).encode()
        result = self._client().create_room(name="Test Room", topic="A test topic")
        self.assertEqual(result["room_id"], "!newroom:example.com")

    @patch("urllib.request.urlopen")
    def test_create_room_sends_name_and_topic(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value.read.return_value = b'{"room_id": "!r"}'
        self._client().create_room(name="Fleet Room", topic="Fleet coordination")
        req: urllib.request.Request = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode())
        self.assertEqual(body["name"], "Fleet Room")
        self.assertEqual(body["topic"], "Fleet coordination")


if __name__ == "__main__":
    unittest.main()