"""
tests/test_crab.py — unit tests for fleet_kit.crab.Crab and Crabs
"""
import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

example_dir = "/home/ubuntu/.openclaw/workspace/repos/fleet-kit"
sys.path.insert(0, example_dir)

KIT_DIR = f"{example_dir}/fleet_kit"

def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

import importlib

keeper_mod = _load("keeper", f"{KIT_DIR}/keeper.py")
plato_mod = _load("plato", f"{KIT_DIR}/plato.py")
crab_mod = _load("crab", f"{KIT_DIR}/crab.py")

Crab = crab_mod.Crab
Crabs = crab_mod.Crabs
KeeperClient = keeper_mod.KeeperClient
PlatoClient = plato_mod.PlatoClient


class TestCrab(unittest.TestCase):
    """Tests for Crab (single agent shell)."""

    def setUp(self):
        self.crab = Crab("test-crab", role="scout")

    def test_register_posts_to_keeper(self):
        """register() should POST to /register with name and capabilities."""
        with patch.object(self.crab._keeper, "_post") as mock_post:
            mock_post.return_value = {"status": "registered", "name": "test-crab"}
            result = self.crab.register(capabilities=["exploration", "coding"])
            payload = mock_post.call_args[0][1]
            self.assertEqual(payload["name"], "test-crab")
            self.assertEqual(payload["capabilities"], ["exploration", "coding"])
            self.assertEqual(result["status"], "registered")

    def test_register_defaults_capabilities_to_role(self):
        """register() with no capabilities should default to [role]."""
        crab = Crab("my-agent", role="builder")
        with patch.object(crab._keeper, "_post") as mock_post:
            mock_post.return_value = {"status": "registered", "name": "my-agent"}
            crab.register()
            payload = mock_post.call_args[0][1]
            self.assertEqual(payload["capabilities"], ["builder"])

    def test_heart_sends_heartbeat(self):
        """heart() should POST to /heartbeat with name and load."""
        with patch.object(self.crab._keeper, "_post") as mock_post:
            mock_post.return_value = {"status": "ack", "active_agents": 5}
            result = self.crab.heart(load=0.3, status="active")
            payload = mock_post.call_args[0][1]
            self.assertEqual(payload["name"], "test-crab")
            self.assertEqual(payload["load"], 0.3)
            self.assertEqual(result["status"], "ack")

    def test_say_posts_tile_to_plato(self):
        """say() should submit a tile to PLATO with the message as answer."""
        with patch.object(self.crab._plato, "_post") as mock_post:
            mock_post.return_value = {"status": "accepted", "tile_hash": "abc123"}
            result = self.crab.say("All systems nominal.", domain="fleet-ops")
            payload = mock_post.call_args[0][1]
            self.assertEqual(payload["answer"], "All systems nominal.")
            self.assertEqual(payload["domain"], "fleet-ops")
            self.assertIn("scout", payload["tags"])
            self.assertEqual(result["tile_hash"], "abc123")

    def test_say_uses_fleet_general_by_default(self):
        """say() with no domain should default to fleet-general."""
        with patch.object(self.crab._plato, "_post") as mock_post:
            mock_post.return_value = {"status": "accepted"}
            self.crab.say("Hello, fleet.")
            payload = mock_post.call_args[0][1]
            self.assertEqual(payload["domain"], "fleet-general")

    def test_status_returns_agent_record(self):
        """status() should GET /agent/<name> and return the record."""
        with patch.object(self.crab._keeper, "_get") as mock_get:
            mock_get.return_value = {"name": "test-crab", "status": "active", "capabilities": ["scout"]}
            result = self.crab.status()
            self.assertEqual(mock_get.call_args[0][0], "/agent/test-crab")
            self.assertEqual(result["name"], "test-crab")
            self.assertEqual(result["status"], "active")


class TestCrabs(unittest.TestCase):
    """Tests for Crabs (fleet manager)."""

    def setUp(self):
        self.crabs = Crabs()

    def test_list_returns_crabs_from_agents(self):
        """list() should return a Crab for each registered agent."""
        with patch.object(self.crabs._keeper, "_get") as mock_get:
            mock_get.return_value = [
                {"name": "scout-1", "capabilities": ["explore"]},
                {"name": "oracle1", "capabilities": ["coordinate"]},
            ]
            result = self.crabs.list()
            self.assertEqual(len(result), 2)
            self.assertIsInstance(result[0], Crab)
            self.assertEqual(result[0].name, "scout-1")
            self.assertEqual(result[1].name, "oracle1")

    def test_list_active_only_filters(self):
        """list(active_only=True) should hit /agents/active endpoint."""
        with patch.object(self.crabs._keeper, "_get") as mock_get:
            mock_get.return_value = []
            self.crabs.list(active_only=True)
            self.assertEqual(mock_get.call_args[0][0], "/agents/active")

    def test_find_returns_crab_when_exists(self):
        """find() should return a Crab if the agent is registered."""
        with patch.object(self.crabs._keeper, "_get") as mock_get:
            mock_get.return_value = {"name": "oracle1", "status": "active"}
            result = self.crabs.find("oracle1")
            self.assertIsInstance(result, Crab)
            self.assertEqual(result.name, "oracle1")

    def test_find_returns_none_when_not_found(self):
        """find() should return None if the agent doesn't exist."""
        with patch.object(self.crabs._keeper, "_get") as mock_get:
            mock_get.return_value = {"error": "not found"}
            result = self.crabs.find("ghost-agent")
            self.assertIsNone(result)

    def test_deploy_crab_registers_and_returns(self):
        """deploy_crab() should register the new agent and return a Crab."""
        # Mock the keeper on the Crabs instance so deploy_crab's new Crab uses it
        mock_post = MagicMock(return_value={"status": "registered", "name": "new-scout"})
        with patch.object(self.crabs._keeper, "_post", mock_post):
            result = self.crabs.deploy_crab("new-scout", role="scout")
            self.assertIsInstance(result, Crab)
            self.assertEqual(result.name, "new-scout")
            payload = mock_post.call_args[0][1]
            self.assertEqual(payload["name"], "new-scout")
            self.assertEqual(payload["capabilities"], ["scout"])

    def test_deploy_crab_with_custom_capabilities(self):
        """deploy_crab() should accept custom capabilities list."""
        mock_post = MagicMock(return_value={"status": "registered"})
        with patch.object(self.crabs._keeper, "_post", mock_post):
            self.crabs.deploy_crab("custom-agent", role="research", capabilities=["ml", "analysis"])
            payload = mock_post.call_args[0][1]
            self.assertEqual(payload["capabilities"], ["ml", "analysis"])


if __name__ == "__main__":
    unittest.main()