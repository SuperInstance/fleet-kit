"""
fleet_kit.plato — PLATO Room Server client.

HMAC-signed client for the PLATO room server at localhost:8847.
Uses urllib only (no external dependencies).

Example:
    client = PlatoClient()
    client.submit_tile("general", "What is a船舶?", "A ship.", ["航海"], 0.9)
    room = client.get_room("general")
    print(room["tile_count"])
"""
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

__all__ = ["PlatoClient"]


class PlatoClient:
    """HMAC-signed client for PLATO room server at localhost:8847.

    Args:
        base_url: Base URL of the PLATO server. Defaults to http://127.0.0.1:8847.
        secret: HMAC signing secret. Reads PLATO_SECRET from environment if not given.

    Attributes:
        base_url: Base URL of the PLATO server.
        secret: HMAC signing secret used for tile signatures.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8847", secret: Optional[str] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.secret = secret or os.environ.get("PLATO_SECRET", "cocapn-fleet-2024")

    def _sign(self, data: Dict[str, Any]) -> str:
        """Compute HMAC-SHA256 signature for a tile dict.

        Args:
            data: Tile data to sign. Must be JSON-serializable.

        Returns:
            Hex digest of the HMAC-SHA256 signature.
        """
        payload = json.dumps(data, sort_keys=True, default=str)
        return hmac.new(
            self.secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

    def _get(self, path: str) -> Dict[str, Any]:
        """Make a GET request to the PLATO server.

        Args:
            path: URL path (e.g. "/status").

        Returns:
            Parsed JSON response.

        Raises:
            urllib.error.HTTPError: On non-2xx status codes.
        """
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())

    def _post(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make a POST request to the PLATO server.

        Args:
            path: URL path (e.g. "/submit").
            data: JSON-serializable body.

        Returns:
            Parsed JSON response.

        Raises:
            urllib.error.HTTPError: On non-2xx status codes.
        """
        url = f"{self.base_url}{path}"
        body = json.dumps(data, default=str).encode()
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    # ── Status ─────────────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        """Return PLATO server status and room summary.

        Returns:
            Dict with keys: status, version, uptime, rooms dict, total_tiles, etc.
        """
        return self._get("/status")

    def tile_count(self) -> int:
        """Return total number of tiles across all rooms.

        Returns:
            Total tile count, or 0 on error.
        """
        try:
            return self.status().get("total_tiles", 0)
        except Exception:
            return 0

    # ── Rooms ───────────────────────────────────────────────────────────────────

    def get_room(self, domain: str) -> Dict[str, Any]:
        """Return full room data for a domain.

        Args:
            domain: Room/domain name (e.g. "general", "knowledge").

        Returns:
            Room dict with keys: tiles (list), tile_count, created, etc.
            Returns a placeholder dict if room does not exist.
        """
        try:
            return self._get(f"/rooms/{domain}")
        except urllib.error.HTTPError:
            return {"tiles": [], "tile_count": 0}

    def get_tiles(self, domain: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Return tiles from a room, up to a limit.

        Args:
            domain: Room/domain name.
            limit: Maximum tiles to return. Defaults to 100.

        Returns:
            List of tile dicts from the room.
        """
        room = self.get_room(domain)
        return room.get("tiles", [])[:limit]

    def delete_room(self, domain: str) -> Dict[str, Any]:
        """Delete a room by removing its last tile (server-side dedup endpoint).

        This calls the server's dedup endpoint which removes duplicate tiles.
        For true room deletion, use the server's DELETE /room/<name> endpoint directly.

        Args:
            domain: Room/domain name to delete.

        Returns:
            Server response dict.
        """
        try:
            return self._post(f"/room/{domain}/dedup", {})
        except Exception as e:
            return {"error": str(e)}

    # ── Tiles ───────────────────────────────────────────────────────────────────

    def submit_tile(
        self,
        domain: str,
        question: str,
        answer: str,
        tags: Optional[List[str]] = None,
        confidence: float = 0.5,
    ) -> Dict[str, Any]:
        """Submit a tile to a PLATO room. Tiles are HMAC-signed.

        Args:
            domain: Room/domain name for the tile.
            question: The question or key (tile question field).
            answer: The answer or value (tile answer field).
            tags: Optional list of string tags.
            confidence: Confidence score between 0.0 and 1.0.

        Returns:
            Server response dict with keys: status, room, tile_hash, etc.
        """
        tile: Dict[str, Any] = {
            "domain": domain,
            "question": question,
            "answer": answer,
            "tags": tags or [],
            "confidence": confidence,
            "agent": "fleet-kit",
            "timestamp": time.time(),
        }
        tile["signature"] = self._sign(tile)
        try:
            return self._post("/submit", tile)
        except urllib.error.HTTPError as e:
            body = e.read()
            try:
                return {"error": json.loads(body), "status": e.code}
            except Exception:
                return {"error": str(e), "status": e.code}