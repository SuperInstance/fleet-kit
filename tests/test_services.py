"""Unit tests for fleet_kit.services."""
from unittest.mock import patch, MagicMock
import pytest
from fleet_kit.services import TileGate, RoomManager, run_server


# ── TileGate ────────────────────────────────────────────────────────────────

class TestTileGate:
    def test_pass_all_checks(self):
        gate = TileGate(min_length=20, max_tags=5, confidence_range=(0.0, 1.0))
        result = gate.validate(
            domain="math",
            question="What is 2+2?",
            answer="Four is the result of 2+2.",
            tags=["math", "arithmetic"],
            confidence=0.9,
        )
        assert result["valid"] is True
        assert result["gate"] == "pass"

    def test_fail_answer_too_short(self):
        gate = TileGate(min_length=20)
        result = gate.validate(
            domain="math", question="x?", answer="Four", tags=[], confidence=0.5
        )
        assert result["valid"] is False
        assert result["gate"] == "len"

    def test_fail_too_many_tags(self):
        gate = TileGate(max_tags=2)
        result = gate.validate(
            domain="bio",
            question="What is DNA?",
            answer="DNA carries genetic information.",
            tags=["gene", "RNA", "chromosomes"],
            confidence=0.5,
        )
        assert result["valid"] is False
        assert result["gate"] == "tags"

    def test_fail_confidence_out_of_range(self):
        gate = TileGate(confidence_range=(0.0, 1.0))
        result = gate.validate(
            domain="hist",
            question="When did WWI start?",
            answer="World War I started in 1914.",
            tags=["history"],
            confidence=1.5,
        )
        assert result["valid"] is False
        assert result["gate"] == "conf"

    def test_custom_thresholds(self):
        gate = TileGate(min_length=5, max_tags=3, confidence_range=(0.0, 0.5))
        assert gate.validate(
            domain="sci",
            question="What is H2O?",
            answer="Water.",
            tags=["chem"],
            confidence=0.25,
        )["valid"] is True
        assert gate.validate(
            domain="sci",
            question="What is H2O?",
            answer="Water is H2O.",
            tags=["chem"],
            confidence=0.99,
        )["valid"] is False


# ── RoomManager ──────────────────────────────────────────────────────────────

class TestRoomManager:
    @patch("fleet_kit.services.PlatoClient")
    def test_create_room(self, MockPlato):
        rm = RoomManager()
        mock_resp = {"status": "created", "domain": "math"}
        MockPlato.return_value.post.return_value = mock_resp
        assert rm.create_room("math") == mock_resp
        MockPlato.return_value.post.assert_called_once_with("room/math", json={})

    @patch("fleet_kit.services.PlatoClient")
    def test_list_rooms(self, MockPlato):
        rm = RoomManager()
        MockPlato.return_value.get.return_value = [{"domain": "math"}, {"domain": "bio"}]
        assert rm.list_rooms() == [{"domain": "math"}, {"domain": "bio"}]
        MockPlato.return_value.get.assert_called_once_with("rooms")

    @patch("fleet_kit.services.PlatoClient")
    def test_delete_room(self, MockPlato):
        rm = RoomManager()
        MockPlato.return_value.delete.return_value = {"status": "deleted"}
        assert rm.delete_room("math") == {"status": "deleted"}
        MockPlato.return_value.delete.assert_called_once_with("room/math")

    @patch("fleet_kit.services.PlatoClient")
    def test_tile_count_returns_count(self, MockPlato):
        rm = RoomManager()
        MockPlato.return_value.get.return_value = {"tiles": [{}, {}, {}]}
        assert rm.tile_count("math") == 3

    @patch("fleet_kit.services.PlatoClient")
    def test_tile_count_missing_tiles_key(self, MockPlato):
        rm = RoomManager()
        MockPlato.return_value.get.return_value = {}
        assert rm.tile_count("empty") == 0

    @patch("fleet_kit.services.PlatoClient")
    def test_tile_count_non_dict_response(self, MockPlato):
        rm = RoomManager()
        MockPlato.return_value.get.return_value = []
        assert rm.tile_count("empty") == 0

    @patch("fleet_kit.services.PlatoClient")
    def test_custom_base_url(self, MockPlato):
        rm = RoomManager(plato_base_url="http://other:8847")
        assert rm.plato_base_url == "http://other:8847"