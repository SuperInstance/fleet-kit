"""
fleet_kit.matrix — Fleet Matrix bridge for agent-to-agent comms.
Zero external dependencies (urllib only, Python 3.10+).
"""
import json
import os
import time
import urllib.request


class MatrixClient:
    """Client for Conduwuit Matrix homeserver.

    Args:
        base_url: Base URL of the Matrix homeserver (default http://127.0.0.1:6167).
        token:    Access token. Reads MATRIX_ACCESS_TOKEN from env if not provided.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:6167", token: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.token = token or os.environ.get("MATRIX_ACCESS_TOKEN")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict:
        """Build request headers, including Authorization if a token is set."""
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _room_url(self, room_id: str, path: str) -> str:
        """Build the full URL for a room-scoped endpoint."""
        return f"{self.base_url}/_matrix/client/v3/rooms/{room_id}/{path}"

    def _put(self, url: str, body: dict, timeout: int = 10) -> dict:
        """Issue a PUT request and return parsed JSON."""
        data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, method="PUT", headers=self._headers())
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())

    def _get(self, url: str, timeout: int = 10) -> dict | list:
        """Issue a GET request and return parsed JSON."""
        req = urllib.request.Request(url, headers=self._headers())
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())

    def _post(self, url: str, body: dict, timeout: int = 10) -> dict:
        """Issue a POST request and return parsed JSON."""
        data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, method="POST", headers=self._headers())
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def status(self) -> dict:
        """Return the server's version and SDK version."""
        url = f"{self.base_url}/_matrix/client/versions"
        return self._get(url)

    def send_room(self, room_id: str, message: str) -> dict:
        """Send a plain-text message to a Matrix room.

        Args:
            room_id: Matrix room ID (e.g. "!z5oIJTqor4UUZliQp1").
            message: Message body to send.

        Returns:
            Server response dict with ``event_id``.
        """
        txn_id = str(int(time.time() * 1000))
        return self._put(
            self._room_url(room_id, f"send/m.room.message/{txn_id}"),
            {"msgtype": "m.text", "body": message},
        )

    def send_dm(self, user_id: str, message: str) -> dict:
        """Send a direct message to a user by creating a DM room and sending to it.

        Args:
            user_id: Matrix user ID (e.g. ``@oracle1:conduwuit``).
            message: Message body to send.

        Returns:
            Server response dict from ``create_room``.
        """
        room = self.create_room(name=f"DM-{user_id}", topic=f"Direct messages with {user_id}")
        room_id = room.get("room_id")
        if room_id:
            self.send_room(room_id, message)
        return room

    def get_messages(self, room_id: str, limit: int = 20) -> list:
        """Fetch the most recent messages from a room.

        Args:
            room_id: Matrix room ID to fetch from.
            limit:   Maximum number of events to return (default 20).

        Returns:
            List of event dicts from the ``chunk`` field.
        """
        url = f"{self._room_url(room_id, 'messages')}?limit={limit}&dir=b"
        data = self._get(url)
        return data.get("chunk", [])

    def list_rooms(self) -> list:
        """Return a list of all joined rooms for the authenticated user.

        Returns:
            List of room summary dicts.
        """
        url = f"{self.base_url}/_matrix/client/v3/joined_rooms"
        return self._get(url)

    def create_room(self, name: str, topic: str = "") -> dict:
        """Create a new Matrix room.

        Args:
            name:  Display name for the room.
            topic: Optional room topic.

        Returns:
            Server response dict containing the new ``room_id``.
        """
        return self._post(
            f"{self.base_url}/_matrix/client/v3/create_room",
            {"name": name, "topic": topic},
        )