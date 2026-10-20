"""Fail-closed tests for the independent ML workspace execution gate."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_workspace import run, digest

class WorkspaceAdmissionTests(unittest.TestCase):
    def test_missing_compiler_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises((OSError, ValueError)):
                run(SimpleNamespace(workspace=folder,
                    compiler=folder + "/definitely-missing-compiler",
                    manifest=folder + "/missing-manifest"))


    def test_full_runner_refuses_missing_compiler_digest_before_git_or_guest(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            binary=root / "synthetic-executable"
            binary.write_text("#!/bin/sh\\nexit 0\\n")
            binary.chmod(0o700)
            args=SimpleNamespace(workspace=folder,compiler=str(binary),
                                 compiler_sha256=None,manifest=str(root/"manifest.json"))
            with patch("run_workspace.git", side_effect=AssertionError("no Git probe")):
                with patch("run_workspace.execute", side_effect=AssertionError("no guest")):
                    with self.assertRaisesRegex(ValueError, "explicit --compiler-sha256"):
                        run(args)

    def test_full_runner_refuses_mismatched_compiler_digest_before_git_or_guest(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            binary=root / "synthetic-executable"
            binary.write_text("#!/bin/sh\\nexit 0\\n")
            binary.chmod(0o700)
            args=SimpleNamespace(workspace=folder,compiler=str(binary),
                                 compiler_sha256="a"*64,manifest=str(root/"manifest.json"))
            with patch("run_workspace.git", side_effect=AssertionError("no Git probe")):
                with patch("run_workspace.execute", side_effect=AssertionError("no guest")):
                    with self.assertRaisesRegex(ValueError, "compiler binary SHA-256 mismatch"):
                        run(args)

if __name__ == "__main__":
    unittest.main()
