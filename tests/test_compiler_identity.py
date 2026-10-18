"""Compiler identity gates use disposable shell fixtures, never Oreslang guest execution."""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_workspace import admit_compiler, digest

class CompilerIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.compiler = self.root / "synthetic-compiler"
        self.compiler.write_text("#!/bin/sh\\nexit 0\\n")
        self.compiler.chmod(0o700)
        self.expected = digest(self.compiler)

    def test_exact_digest_admitted_without_executing_binary(self):
        binary, observed = admit_compiler(str(self.compiler), self.expected, self.workspace)
        self.assertEqual(binary, self.compiler)
        self.assertEqual(observed, self.expected)

    def test_mismatch_rejected_before_probe(self):
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            admit_compiler(str(self.compiler), "a" * 64, self.workspace)

    def test_missing_digest_rejected(self):
        with self.assertRaisesRegex(ValueError, "explicit --compiler-sha256"):
            admit_compiler(str(self.compiler), None, self.workspace)

    def test_uppercase_digest_rejected(self):
        with self.assertRaisesRegex(ValueError, "explicit --compiler-sha256"):
            admit_compiler(str(self.compiler), self.expected.upper(), self.workspace)

    def test_mutated_executable_rejected(self):
        self.compiler.write_text("#!/bin/sh\\nexit 99\\n")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            admit_compiler(str(self.compiler), self.expected, self.workspace)

    def test_compiler_inside_workspace_rejected(self):
        located = self.workspace / "untrusted-script"
        located.write_bytes(self.compiler.read_bytes())
        located.chmod(0o700)
        with self.assertRaisesRegex(ValueError, "outside mutable source workspace"):
            admit_compiler(str(located), digest(located), self.workspace)

    def test_symlinked_compiler_rejected(self):
        linked = self.root / "binary-link"
        linked.symlink_to(self.compiler)
        with self.assertRaisesRegex(ValueError, "non-symlink"):
            admit_compiler(str(linked), self.expected, self.workspace)

    def test_relative_compiler_path_rejected(self):
        with self.assertRaisesRegex(ValueError, "absolute non-symlink"):
            admit_compiler("synthetic-compiler", self.expected, self.workspace)

    def test_missing_executable_permission_rejected(self):
        self.compiler.chmod(0o600)
        with self.assertRaisesRegex(ValueError, "absolute executable file"):
            admit_compiler(str(self.compiler), self.expected, self.workspace)

if __name__ == "__main__":
    unittest.main()
