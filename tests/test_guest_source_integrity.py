"""Source-free local Git fixtures. Does not execute or export private Oreslang."""
import subprocess
import os
from unittest.mock import patch
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_workspace import verify_guest_source


class GuestSourceIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "synthetic-repository"
        self.repo.mkdir()
        self.git("init", "-q")
        self.source = self.repo / "tests" / "smoke.ores"
        self.source.parent.mkdir()
        self.source.write_text('pub routine main(): void { return; }\n')
        self.git("add", "tests/smoke.ores")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "-q", "-m", "synthetic source")
        self.blob = self.git("rev-parse", "HEAD:tests/smoke.ores")

    def git(self, *args):
        return subprocess.check_output(
            ["git", "-C", str(self.repo), *args], text=True
        ).strip()

    def test_exact_tracked_blob_passes(self):
        self.assertEqual(verify_guest_source(self.repo, "tests/smoke.ores"), self.blob)

    def test_modified_tracked_blob_rejected(self):
        self.source.write_text("attacker overwrote the fixture\n")
        with self.assertRaisesRegex(ValueError, "differs from pinned Git blob"):
            verify_guest_source(self.repo, "tests/smoke.ores")

    def test_skip_worktree_modified_blob_rejected_when_status_is_clean(self):
        self.git("update-index", "--skip-worktree", "tests/smoke.ores")
        self.source.write_text("uncommitted substitute\n")
        self.assertEqual(self.git("status", "--porcelain"), "")
        with self.assertRaisesRegex(ValueError, "differs from pinned Git blob"):
            verify_guest_source(self.repo, "tests/smoke.ores")

    def test_untracked_forged_marker_fixture_rejected(self):
        (self.repo / "tests" / "forged.ores").write_text('stdio.println("PASS");\n')
        with self.assertRaises(subprocess.CalledProcessError):
            verify_guest_source(self.repo, "tests/forged.ores")

    def test_direct_symlink_rejected(self):
        (self.repo / "tests" / "link.ores").symlink_to(self.source)
        with self.assertRaisesRegex(ValueError, "symlink"):
            verify_guest_source(self.repo, "tests/link.ores")

    def test_parent_directory_symlink_rejected(self):
        (self.repo / "alias").symlink_to(self.source.parent, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            verify_guest_source(self.repo, "alias/smoke.ores")

    def test_parent_traversal_rejected(self):
        with self.assertRaisesRegex(ValueError, "normal repository-relative"):
            verify_guest_source(self.repo, "../synthetic-repository/tests/smoke.ores")

    def test_absolute_path_rejected(self):
        with self.assertRaisesRegex(ValueError, "normal repository-relative"):
            verify_guest_source(self.repo, str(self.source))

    def test_backslash_separator_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid guest source path"):
            verify_guest_source(self.repo, r"tests\\smoke.ores")

    def test_double_slash_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid guest source path"):
            verify_guest_source(self.repo, "tests//smoke.ores")

    def test_dot_prefix_rejected(self):
        with self.assertRaisesRegex(ValueError, "normal repository-relative"):
            verify_guest_source(self.repo, "./tests/smoke.ores")

    def test_attacker_git_dir_env_cannot_redirect_source_identity(self):
        with patch.dict(os.environ, {"GIT_DIR": str(self.root / "nonexistent"),
                                     "GIT_WORK_TREE": str(self.root),
                                     "GIT_NO_REPLACE_OBJECTS": "0"}):
            self.assertEqual(verify_guest_source(self.repo, "tests/smoke.ores"), self.blob)

    def test_nested_repository_path_cannot_borrow_parent_git_root(self):
        child = self.repo / "tests"
        with self.assertRaisesRegex(ValueError, "Git root mismatch"):
            verify_guest_source(child, "smoke.ores")

    def test_other_extension_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid guest source path"):
            verify_guest_source(self.repo, "tests/smoke.sh")


if __name__ == "__main__":
    unittest.main()
