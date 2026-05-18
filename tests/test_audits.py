"""
tests/test_audits.py — unit tests for fleet_kit.audits.RepoAuditor
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

example_dir = "/home/ubuntu/.openclaw/workspace/repos/fleet-kit"
sys.path.insert(0, example_dir)

import importlib.util
spec = importlib.util.spec_from_file_location("audits", f"{example_dir}/fleet_kit/audits.py")
audits_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audits_module)
RepoAuditor = audits_module.RepoAuditor
_score = audits_module._score


class TestRepoAuditor(unittest.TestCase):
    """Tests for RepoAuditor."""

    def setUp(self):
        """Create auditor with a temp workspace."""
        self.tmp = Path(tempfile.mkdtemp(prefix="auditor_test_"))
        self.auditor = RepoAuditor(workspace_dir=str(self.tmp))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ── audit — missing repo ─────────────────────────────────────────────────

    def test_audit_nonexistent_returns_not_exists(self):
        """audit() should set exists=False for missing directories."""
        result = self.auditor.audit("nonexistent-repo-xyz")
        self.assertFalse(result["exists"])
        self.assertIn("not found", result["issues"][0])

    # ── audit — basic checks ─────────────────────────────────────────────────

    def test_audit_readme_found(self):
        """audit() should set readme=True when README.md exists."""
        (self.tmp / "my-repo").mkdir()
        (self.tmp / "my-repo" / "README.md").touch()
        result = self.auditor.audit("my-repo")
        self.assertTrue(result["readme"])

    def test_audit_license_found(self):
        """audit() should set license=True when LICENSE file exists."""
        (self.tmp / "my-repo").mkdir()
        (self.tmp / "my-repo" / "LICENSE").touch()
        result = self.auditor.audit("my-repo")
        self.assertTrue(result["license"])

    def test_audit_ci_detected(self):
        """audit() should detect .github/workflows as CI."""
        (self.tmp / "my-repo").mkdir()
        (self.tmp / "my-repo" / ".github").mkdir()
        (self.tmp / "my-repo" / ".github" / "workflows").mkdir()
        result = self.auditor.audit("my-repo")
        self.assertTrue(result["ci"])

    # ── audit_all ─────────────────────────────────────────────────────────────

    def test_audit_all_empty_workspace(self):
        """audit_all() should return [] when workspace doesn't exist."""
        auditor = RepoAuditor(workspace_dir="/tmp/nonexistent_dir_abc123")
        self.assertEqual(auditor.audit_all(), [])

    # ── _score ─────────────────────────────────────────────────────────────────

    def test_score_excellent_high(self):
        """_score should return ≥0.8 for well-documented repos."""
        report = {"readme": True, "license": True, "tests": 10, "ci": True, "files": 100}
        self.assertGreaterEqual(_score(report), 0.8)

    def test_score_poor_minimal(self):
        """_score should return low score for empty/bare repos."""
        report = {"readme": False, "license": False, "tests": 0, "ci": False, "files": 0}
        self.assertLess(_score(report), 0.2)

    # ── file_to_plato ──────────────────────────────────────────────────────────

    def test_file_to_plato_calls_submit(self):
        """file_to_plato should call client.submit_tile with audit data."""
        client_instance = MagicMock()
        client_instance.submit_tile.return_value = {"status": "accepted"}
        with patch.object(audits_module.PlatoClient, "__init__", lambda self, **kw: None):
            with patch.object(audits_module.PlatoClient, "submit_tile", client_instance.submit_tile):
                result = self.auditor.file_to_plato({
                    "name": "test-repo",
                    "readme": True,
                    "license": True,
                    "tests": 5,
                    "ci": True,
                    "files": 50,
                    "issues": [],
                    "score": 0.85,
                })
                client_instance.submit_tile.assert_called_once()
                call_kwargs = client_instance.submit_tile.call_args.kwargs
                self.assertEqual(call_kwargs["domain"], "oracle1_infrastructure")
                self.assertIn("test-repo", call_kwargs["question"])
                self.assertGreater(call_kwargs["confidence"], 0.8)

    def test_file_to_plato_issues_included(self):
        """file_to_plato should include issues in the answer."""
        client_instance = MagicMock()
        client_instance.submit_tile.return_value = {"status": "accepted"}
        with patch.object(audits_module.PlatoClient, "__init__", lambda self, **kw: None):
            with patch.object(audits_module.PlatoClient, "submit_tile", client_instance.submit_tile):
                self.auditor.file_to_plato({
                    "name": "bare-repo",
                    "readme": False,
                    "license": False,
                    "tests": 0,
                    "ci": False,
                    "files": 3,
                    "issues": ["No README found", "No LICENSE found"],
                    "score": 0.05,
                })
                answer = client_instance.submit_tile.call_args.kwargs["answer"]
                self.assertIn("No README found", answer)
                self.assertIn("No LICENSE found", answer)


if __name__ == "__main__":
    unittest.main()