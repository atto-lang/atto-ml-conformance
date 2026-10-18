"""Synthetic log tests. No Oreslang compiler or source checkout is involved."""
import json
import subprocess
import tempfile
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from host_receipt import make_receipt, parse_node_summary, parse_python_summary

SHA = "a" * 40
TREE = "b" * 40
NODE = "# tests 73\n# pass 73\n# fail 0\n# skipped 0\n# todo 0\n"
PYTHON = "Ran 18 tests in 0.123s\n\nOK\n"


class HostReceiptTests(unittest.TestCase):
    def test_host_only_receipt(self):
        r = make_receipt(SHA, SHA, TREE, NODE, PYTHON, "REFERENCE_PASS\n")
        self.assertEqual(r["node_host_tests_passed"], 73)
        self.assertEqual(r["python_host_tests_passed"], 18)
        self.assertFalse(r["release_ready"])
        self.assertFalse(r["native_guest_executed"])
        self.assertFalse(r["source_export_authorized"])

    def test_wrong_commit(self):
        with self.assertRaisesRegex(ValueError, "differs"):
            make_receipt(SHA, "c" * 40, TREE, NODE, PYTHON, "REFERENCE_PASS\n")

    def test_invalid_commit(self):
        with self.assertRaisesRegex(ValueError, "invalid Git"):
            make_receipt("main", SHA, TREE, NODE, PYTHON, "REFERENCE_PASS\n")

    def test_wrong_reference_marker(self):
        with self.assertRaisesRegex(ValueError, "reference check"):
            make_receipt(SHA, SHA, TREE, NODE, PYTHON, "FAKE_PASS\n")

    def test_failed_node(self):
        with self.assertRaisesRegex(ValueError, "did not all pass"):
            parse_node_summary(NODE.replace("# fail 0", "# fail 1"))

    def test_skipped_node(self):
        with self.assertRaisesRegex(ValueError, "skips"):
            parse_node_summary(NODE.replace("# skipped 0", "# skipped 1"))

    def test_todo_node(self):
        with self.assertRaisesRegex(ValueError, "skips"):
            parse_node_summary(NODE.replace("# todo 0", "# todo 1"))

    def test_duplicate_node_summary(self):
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            parse_node_summary(NODE + "# tests 73\n")

    def test_missing_node_count(self):
        with self.assertRaisesRegex(ValueError, "missing"):
            parse_node_summary(NODE.replace("# tests 73\n", ""))

    def test_failed_python(self):
        with self.assertRaisesRegex(ValueError, "failed"):
            parse_python_summary(PYTHON.replace("OK", "FAILED (failures=1)"))

    def test_skipped_python(self):
        with self.assertRaisesRegex(ValueError, "summary"):
            parse_python_summary(PYTHON.replace("OK", "OK (skipped=1)"))

    def test_duplicate_python(self):
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            parse_python_summary(PYTHON + PYTHON)


    def test_cli_binds_real_temp_git_commit_and_tree(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            subprocess.run(["git", "init", "-q", d], check=True)
            (root / "test-fixture.txt").write_text("independently authored synthetic text\n")
            subprocess.run(["git", "-C", d, "add", "test-fixture.txt"], check=True)
            subprocess.run(["git", "-C", d, "-c", "user.name=Test",
                            "-c", "user.email=test@example.invalid", "commit", "-q", "-m", "fixture"], check=True)
            head = subprocess.check_output(["git", "-C", d, "rev-parse", "HEAD"], text=True).strip()
            tree = subprocess.check_output(["git", "-C", d, "rev-parse", "HEAD^{tree}"], text=True).strip()
            (root / "node.log").write_text(NODE)
            (root / "python.log").write_text(PYTHON)
            (root / "reference.ok").write_text("REFERENCE_PASS\n")
            script = Path(__file__).resolve().parents[1] / "scripts" / "host_receipt.py"
            arguments = [sys.executable, str(script), "--expected-sha", head,
                         "--node-log", "node.log", "--python-log", "python.log",
                         "--reference-marker", "reference.ok", "--output", "receipt.json"]
            succeeded = subprocess.run(arguments, cwd=root, capture_output=True, text=True)
            self.assertEqual(succeeded.returncode, 0, succeeded.stderr)
            receipt = json.loads((root / "receipt.json").read_text())
            self.assertEqual(receipt["source_commit"], head)
            self.assertEqual(receipt["source_git_tree"], tree)
            self.assertEqual(receipt["evidence_scope"], "HOST_REFERENCE_ONLY")
            self.assertFalse(receipt["private_source_transferred"])
            self.assertFalse(receipt["native_compiler_executed"])
            (root / "receipt.json").unlink()
            arguments[arguments.index(head)] = "f" * 40
            denied = subprocess.run(arguments, cwd=root, capture_output=True, text=True)
            self.assertNotEqual(denied.returncode, 0)
            self.assertFalse((root / "receipt.json").exists())


if __name__ == "__main__":
    unittest.main()
