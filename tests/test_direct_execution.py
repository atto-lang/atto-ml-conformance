"""Host-only adversarial proof of *direct* CLI dispatch, not Oreslang compilation."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_workspace import JOBS, execute


class DirectGuestDispatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "oreslang-tensor"
        (self.repo / "tests").mkdir(parents=True)
        (self.repo / "tests" / "smoke.ores").write_text("not an executable shell script\n")
        self.compiler = self.base / "synthetic-compiler"
        self.marker = "ORES_ML_TENSOR_SMOKE_PASS"

    def compiler_body(self, body):
        self.compiler.write_text("#!/bin/sh\n" + body + "\n")
        self.compiler.chmod(0o700)

    def test_six_guest_programs_are_dispatched_separately(self):
        self.assertEqual(len(JOBS), 6)
        self.assertEqual(len(set((name, source) for name, source, _ in JOBS)), 6)
        self.assertTrue(all(source.endswith(".ores") for _, source, _ in JOBS))
        self.assertTrue(all("|" not in marker for _, _, marker in JOBS))

    def test_direct_compiler_receives_source_not_shell_script(self):
        self.compiler_body(
            'test "$1" = tests/smoke.ores || exit 7\n'
            'printf "%s\\n" ORES_ML_TENSOR_SMOKE_PASS'
        )
        result = execute(self.repo, "tests/smoke.ores", self.compiler, self.marker)
        self.assertEqual(result["source"], "tests/smoke.ores")
        self.assertEqual(result["exit"], 0)
        self.assertTrue(result["exact_marker_present"])

    def test_shell_script_cannot_forge_compiler_success(self):
        scripts = self.repo / "scripts"
        scripts.mkdir()
        (scripts / "test.sh").write_text("#!/bin/sh\nprintf 'ORES_ML_TENSOR_SMOKE_PASS\\n'\n")
        self.compiler_body("exit 23")
        with self.assertRaisesRegex(ValueError, "guest exit 23"):
            execute(self.repo, "tests/smoke.ores", self.compiler, self.marker)

    def test_bogus_marker_rejected_even_on_zero_exit(self):
        self.compiler_body("printf 'INCORRECT_MARKER\\n'")
        with self.assertRaisesRegex(ValueError, "unexpected guest stdout or missing exact success marker"):
            execute(self.repo, "tests/smoke.ores", self.compiler, self.marker)

    def test_extra_stdout_fails_even_with_correct_marker(self):
        self.compiler_body("printf 'ORES_ML_TENSOR_SMOKE_PASS\\nextra output\\n'")
        with self.assertRaisesRegex(ValueError, "unexpected guest stdout"):
            execute(self.repo, "tests/smoke.ores", self.compiler, self.marker)

    def test_nonexistent_fixture_rejected_before_launch(self):
        self.compiler_body("exit 0")
        with self.assertRaises(FileNotFoundError):
            execute(self.repo, "tests/not-present.ores", self.compiler, self.marker)

    def test_symlinked_fixture_rejected_before_launch(self):
        outside = self.base / "outside.ores"
        outside.write_text("untrusted")
        (self.repo / "tests" / "linked.ores").symlink_to(outside)
        self.compiler_body("exit 0")
        with self.assertRaisesRegex(ValueError, "must not be a symlink"):
            execute(self.repo, "tests/linked.ores", self.compiler, self.marker)

    def test_parent_directory_symlink_escape_rejected(self):
        external = self.base / "external"
        external.mkdir()
        (external / "smoke.ores").write_text("untrusted")
        (self.repo / "outside").symlink_to(external, target_is_directory=True)
        self.compiler_body("exit 0")
        with self.assertRaisesRegex(ValueError, "escapes the pinned repository"):
            execute(self.repo, "outside/smoke.ores", self.compiler, self.marker)

    def test_non_ores_source_rejected_before_launch(self):
        self.compiler_body("exit 0")
        with self.assertRaisesRegex(ValueError, "must be a .ores file"):
            execute(self.repo, "scripts/test.sh", self.compiler, self.marker)


if __name__ == "__main__":
    unittest.main()
