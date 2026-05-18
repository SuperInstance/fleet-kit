"""PLATO server-side services extracted for fleet-kit consumers."""

from fleet_kit.plato import PlatoClient

# ── TileGate ────────────────────────────────────────────────────────────────────

class TileGate:
    """Quality gate for tile submissions.

    Validates domain/question/answer/tag/confidence tuples against configurable
    thresholds before they are admitted to a PLATO room.
    """

    def __init__(
        self,
        min_length: int = 20,
        max_tags: int = 5,
        confidence_range: tuple[float, float] = (0.0, 1.0),
    ):
        self.min_length = min_length
        self.max_tags = max_tags
        self.confidence_range = confidence_range

    def validate(
        self,
        domain: str,
        question: str,
        answer: str,
        tags: list[str],
        confidence: float,
    ) -> dict[str, str]:
        """Validate a single tile.

        Returns ``{"valid": bool, "reason": str, "gate": str}``.
        ``gate`` is one of:
        ``"pass"``, ``"len"``, ``"tags"``, ``"conf"``.
        """
        if len(answer) < self.min_length:
            return {
                "valid": False,
                "reason": f"answer too short ({len(answer)} < {self.min_length})",
                "gate": "len",
            }
        if len(tags) > self.max_tags:
            return {
                "valid": False,
                "reason": f"too many tags ({len(tags)} > {self.max_tags})",
                "gate": "tags",
            }
        if not (self.confidence_range[0] <= confidence <= self.confidence_range[1]):
            return {
                "valid": False,
                "reason": (
                    f"confidence out of range "
                    f"({confidence} not in {self.confidence_range})"
                ),
                "gate": "conf",
            }
        return {"valid": True, "reason": "ok", "gate": "pass"}


# ── RoomManager ──────────────────────────────────────────────────────────────

class RoomManager:
    """Lightweight room CRUD backed by the PLATO HTTP API."""

    def __init__(self, plato_base_url: str = "http://127.0.0.1:8847"):
        self.plato_base_url = plato_base_url
        self._plato = PlatoClient(base_url=plato_base_url)

    def create_room(self, domain: str) -> dict:  # noqa: D101
        """Create (or replace) a PLATO room keyed by *domain*."""
        resp = self._plato.post(f"room/{domain}", json={})
        return resp

    def list_rooms(self) -> list[dict]:  # noqa: D101
        """Return a list of all known rooms."""
        resp = self._plato.get("rooms")
        return resp if isinstance(resp, list) else []

    def delete_room(self, domain: str) -> dict:  # noqa: D101
        """Delete a room by *domain*."""
        resp = self._plato.delete(f"room/{domain}")
        return resp

    def tile_count(self, domain: str) -> int:
        """Return the number of tiles currently stored in *domain*."""
        room = self._plato.get(f"room/{domain}")
        if isinstance(room, dict):
            return len(room.get("tiles", []))
        return 0


# ── Server ───────────────────────────────────────────────────────────────────

def run_server(port: int = 8847) -> None:
    """Start a PLATO room HTTP server on *port*.

    This is a placeholder.  The full server lives in
    ``fleet.services.plato`` and must be invoked directly:

    >>> python -m fleet.services.plato
    """
    print("Use fleet.services.plato directly for the full server.")