"""Fail-closed tests for the independent ML workspace execution gate."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_workspace import run

class WorkspaceAdmissionTests(unittest.TestCase):
    def test_missing_compiler_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises((OSError, ValueError)):
                run(SimpleNamespace(workspace=folder,
                    compiler=folder + "/definitely-missing-compiler",
                    manifest=folder + "/missing-manifest"))

if __name__ == "__main__":
    unittest.main()
