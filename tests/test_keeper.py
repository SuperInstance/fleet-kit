"""
tests/test_keeper.py — tests for fleet_kit.keeper.KeeperClient
"""
import sys
import unittest
from unittest.mock import patch, MagicMock

# Bypass fleet_kit.__init__ (which imports a missing services module).
# Import keeper.py directly via file loader.
import importlib.util
spec = importlib.util.spec_from_file_location("keeper", "fleet_kit/keeper.py")
keeper_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(keeper_mod)
KeeperClient = keeper_mod.KeeperClient


class TestKeeperClient(unittest.TestCase):

    def setUp(self):
        self.client = KeeperClient()

    # ── status() ────────────────────────────────────────────────────────────

    @patch("urllib.request.urlopen")
    def test_status_returns_dict(self, mock_urlopen):
        fake = MagicMock()
        fake.read.return_value = b'{"status": "active", "agents_registered": 3, "agents_active": 2}'
        fake.__enter__ = MagicMock(return_value=fake)
        fake.__exit__ = MagicMock(return_value=None)
        mock_urlopen.return_value = fake

        result = self.client.status()
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["agents_registered"], 3)

    # ── register_agent() ───────────────────────────────────────────────────

    @patch("urllib.request.urlopen")
    def test_register_agent(self, mock_urlopen):
        fake = MagicMock()
        fake.read.return_value = b'{"status": "registered", "name": "oracle1"}'
        fake.__enter__ = MagicMock(return_value=fake)
        fake.__exit__ = MagicMock(return_value=None)
        mock_urlopen.return_value = fake

        result = self.client.register_agent("oracle1", "planner", tags=["alpha"])
        self.assertEqual(result["status"], "registered")
        self.assertEqual(result["name"], "oracle1")

    # ── list_agents() ─────────────────────────────────────────────────────

    @patch("urllib.request.urlopen")
    def test_list_agents(self, mock_urlopen):
        fake = MagicMock()
        fake.read.return_value = b'[{"name": "oracle1"}, {"name": "jetson1"}]'
        fake.__enter__ = MagicMock(return_value=fake)
        fake.__exit__ = MagicMock(return_value=None)
        mock_urlopen.return_value = fake

        agents = self.client.list_agents()
        self.assertEqual(len(agents), 2)
        self.assertEqual(agents[0]["name"], "oracle1")

    # ── agents_active() ────────────────────────────────────────────────────

    @patch("urllib.request.urlopen")
    def test_agents_active(self, mock_urlopen):
        fake = MagicMock()
        fake.read.return_value = b'{"status": "active", "agents_registered": 3, "agents_active": 5}'
        fake.__enter__ = MagicMock(return_value=fake)
        fake.__exit__ = MagicMock(return_value=None)
        mock_urlopen.return_value = fake

        count = self.client.agents_active()
        self.assertEqual(count, 5)


if __name__ == "__main__":
    unittest.main()
