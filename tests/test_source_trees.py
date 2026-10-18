"""Negative admission tests: no private code or compiler is invoked."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_workspace import run


REPOS = ("oreslang-tensor", "oreslang-autograd", "oreslang-ml")


class SourceTreeAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in REPOS:
            (self.root / name).mkdir()
        self.compiler = self.root / "fake-never-executed"
        self.compiler.write_text("#!/bin/sh\nexit 99\n")
        self.compiler.chmod(0o700)
        self.doc = {
            "schema_version": "oreslang-ml-workspace/v1",
            "repositories": {name: "a" * 40 for name in REPOS},
            "source_trees": {name: "b" * 40 for name in REPOS},
        }
        self.path = self.root / "manifest.json"

    def attempt(self):
        self.path.write_text(json.dumps(self.doc))
        args = SimpleNamespace(workspace=str(self.root),
                               compiler=str(self.compiler),
                               manifest=str(self.path))
        with patch("run_workspace.execute", side_effect=AssertionError("guest must not run")):
            with patch("run_workspace.git", side_effect=self.fake_git):
                return run(args)

    @staticmethod
    def fake_git(repo, *args):
        if args[:2] == ("rev-parse", "HEAD"):
            return "a" * 40
        if args[:3] == ("show", "-s", "--format=%T"):
            return "c" * 40
        raise AssertionError("unexpected Git probe")

    def test_missing_tree_manifest_denied(self):
        del self.doc["source_trees"]
        with self.assertRaisesRegex(ValueError, "tree"):
            self.attempt()

    def test_mismatched_tree_denied_before_guest(self):
        with self.assertRaisesRegex(ValueError, "tree mismatch"):
            self.attempt()

    def test_invalid_tree_digest_denied(self):
        self.doc["source_trees"]["oreslang-ml"] = "invalid"
        with self.assertRaisesRegex(ValueError, "tree identity"):
            self.attempt()


if __name__ == "__main__":
    unittest.main()
