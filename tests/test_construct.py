"""
Tests for fleet_kit.construct — Agent Lifecycle Management

Mocks KeeperClient at the correct location — within the construct module's
namespace where it is looked up at call time.
"""
import sys
import unittest
from unittest.mock import patch, MagicMock

# Load modules directly to bypass the broken fleet_kit.__init__ import chain.
import importlib.util

spec = importlib.util.spec_from_file_location("keeper", "fleet_kit/keeper.py")
keeper_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(keeper_mod)
KeeperClient = keeper_mod.KeeperClient
sys.modules["fleet_kit.keeper"] = keeper_mod

spec2 = importlib.util.spec_from_file_location("construct", "fleet_kit/construct.py")
construct_mod = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(construct_mod)
build_agent = construct_mod.build_agent
deploy_pipeline = construct_mod.deploy_pipeline
teardown_agent = construct_mod.teardown_agent


class TestBuildAgent(unittest.TestCase):
    """Tests for build_agent()."""

    @patch.object(construct_mod, "KeeperClient")
    def test_build_agent_registers_with_keeper(self, MockKC):
        mock_instance = MagicMock()
        mock_instance.register_agent.return_value = {
            "status": "registered",
            "name": "test-agent",
        }
        MockKC.return_value = mock_instance

        result = build_agent("test-agent", "researcher", capabilities=["web"])

        mock_instance.register_agent.assert_called_once_with(
            "test-agent", "researcher", tags=["web"]
        )
        self.assertEqual(result["status"], "registered")
        self.assertEqual(result["name"], "test-agent")

    @patch.object(construct_mod, "KeeperClient")
    def test_build_agent_defaults_tags_to_none(self, MockKC):
        mock_instance = MagicMock()
        mock_instance.register_agent.return_value = {"status": "registered", "name": "agent1"}
        MockKC.return_value = mock_instance

        build_agent("agent1", "builder")

        mock_instance.register_agent.assert_called_once_with("agent1", "builder", tags=None)

    @patch.object(construct_mod, "KeeperClient")
    def test_build_agent_custom_base_url(self, MockKC):
        mock_instance = MagicMock()
        mock_instance.register_agent.return_value = {"status": "registered", "name": "agent2"}
        MockKC.return_value = mock_instance

        build_agent("agent2", "planner", base_url="http://localhost:9000")

        MockKC.assert_called_once_with(base_url="http://localhost:9000")


class TestDeployPipeline(unittest.TestCase):
    """Tests for deploy_pipeline()."""

    @patch.object(construct_mod, "KeeperClient")
    def test_deploy_pipeline_returns_step_statuses(self, MockKC):
        mock_instance = MagicMock()
        mock_instance.register_agent.return_value = {"status": "registered", "name": "pipe-agent"}
        MockKC.return_value = mock_instance

        result = deploy_pipeline(
            "pipe-agent", "builder",
            pipeline_steps=[
                {"name": "ingest", "action": "start"},
                {"name": "process", "action": "restart"},
                {"name": "export", "action": "stop"},
            ],
        )

        self.assertEqual(result["agent"], "pipe-agent")
        self.assertEqual(len(result["steps"]), 3)
        self.assertEqual(result["steps"][0]["status"], "deployed")
        self.assertEqual(result["steps"][1]["action"], "restart")
        self.assertEqual(result["steps"][2]["action"], "stop")

    @patch.object(construct_mod, "KeeperClient")
    def test_deploy_pipeline_invalid_action_returns_error(self, MockKC):
        mock_instance = MagicMock()
        mock_instance.register_agent.return_value = {"status": "registered", "name": "bad-agent"}
        MockKC.return_value = mock_instance

        result = deploy_pipeline(
            "bad-agent", "researcher",
            pipeline_steps=[{"name": "step1", "action": "invalid"}],
        )

        self.assertEqual(result["steps"][0]["status"], "error")
        self.assertIn("Invalid action", result["steps"][0]["error"])

    @patch.object(construct_mod, "KeeperClient")
    def test_deploy_pipeline_defaults_to_start_step(self, MockKC):
        mock_instance = MagicMock()
        mock_instance.register_agent.return_value = {"status": "registered", "name": "default-agent"}
        MockKC.return_value = mock_instance

        result = deploy_pipeline("default-agent", "planner")

        self.assertEqual(result["agent"], "default-agent")
        self.assertEqual(len(result["steps"]), 1)
        self.assertEqual(result["steps"][0]["action"], "start")


class TestTeardownAgent(unittest.TestCase):
    """Tests for teardown_agent()."""

    @patch.object(construct_mod, "KeeperClient")
    def test_teardown_agent_returns_removal_confirmation(self, MockKC):
        mock_instance = MagicMock()
        mock_instance.heartbeat.return_value = {"status": "ack"}
        MockKC.return_value = mock_instance

        result = teardown_agent("old-agent")

        self.assertEqual(result["status"], "removed")
        self.assertEqual(result["name"], "old-agent")
        mock_instance.heartbeat.assert_called_once_with("old-agent", load=1.0, status="decommissioned")

    @patch.object(construct_mod, "KeeperClient")
    def test_teardown_agent_sends_decommission_heartbeat(self, MockKC):
        mock_instance = MagicMock()
        mock_instance.heartbeat.return_value = {"status": "ack"}
        MockKC.return_value = mock_instance

        teardown_agent("decom-agent")

        mock_instance.heartbeat.assert_called_once()
        call_kwargs = mock_instance.heartbeat.call_args[1]
        self.assertEqual(call_kwargs["load"], 1.0)
        self.assertEqual(call_kwargs["status"], "decommissioned")


if __name__ == "__main__":
    unittest.main()