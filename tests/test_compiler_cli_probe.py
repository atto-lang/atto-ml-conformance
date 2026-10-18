"""Host-only shell doubles for CLI protocol checks; no Oreslang guest evidence."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from compiler_cli_probe import probe_compiler_cli


class CompilerCliProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'oreslang-tensor'
        (self.repo / 'tests').mkdir(parents=True)
        (self.repo / 'tests' / 'smoke.ores').write_text('pub routine main(): void {}\n')
        self.compiler = self.root / 'fake-cli'

    def fake(self, build_info='{"build_mode":"jvm","default_execution_mode":"jit","guest_execution":"runtime-selected"}',
             reject_negative=True, positive_ok=True, extra=''):
        script = '''#!/bin/sh
if [ "$1" = "--build-info" ]; then
  printf '%s\\n' '__BUILD__'
  exit 0
fi
if [ "$1" = "--check" ]; then
  case "$2" in
    tests/smoke.ores) __POSITIVE__ ;;
    */parse-negative.ores) __NEGATIVE__ ;;
  esac
fi
exit 88
'''.replace('__BUILD__', build_info.replace("'", "'\\''"))
        script = script.replace('__POSITIVE__', 'exit 0' if positive_ok else 'exit 1')
        script = script.replace('__NEGATIVE__', 'echo "syntax error" >&2; exit 1' if reject_negative else 'exit 0')
        self.compiler.write_text(script + extra)
        self.compiler.chmod(0o700)

    def test_well_formed_simulated_cli(self):
        self.fake()
        result = probe_compiler_cli(self.compiler, self.repo)
        self.assertEqual(result['status'], 'CLI_BEHAVIOR_PROBED_UNATTESTED')
        self.assertFalse(result['source_binary_provenance_attested'])
        self.assertFalse(result['guest_executed'])

    def test_invalid_json_rejected(self):
        self.fake(build_info='not-json')
        with self.assertRaisesRegex(ValueError, 'malformed --build-info JSON'):
            probe_compiler_cli(self.compiler, self.repo)

    def test_disallowed_build_mode_rejected(self):
        self.fake(build_info='{"build_mode":"untrusted","default_execution_mode":"jit","guest_execution":"runtime-selected"}')
        with self.assertRaisesRegex(ValueError, 'inconsistent build mode'):
            probe_compiler_cli(self.compiler, self.repo)

    def test_conflicting_mode_capability_rejected(self):
        self.fake(build_info='{"build_mode":"aot","default_execution_mode":"jit","guest_execution":"runtime-selected"}')
        with self.assertRaisesRegex(ValueError, 'inconsistent build mode'):
            probe_compiler_cli(self.compiler, self.repo)

    def test_positive_check_failure_rejected(self):
        self.fake(positive_ok=False)
        with self.assertRaisesRegex(ValueError, 'positive Oreslang smoke'):
            probe_compiler_cli(self.compiler, self.repo)

    def test_invalid_source_accepted_rejected(self):
        self.fake(reject_negative=False)
        with self.assertRaisesRegex(ValueError, 'malformed Oreslang source was accepted'):
            probe_compiler_cli(self.compiler, self.repo)

    def test_missing_or_symlink_positive_rejected(self):
        self.fake()
        source = self.repo / 'tests' / 'smoke.ores'
        source.unlink()
        source.symlink_to(self.compiler)
        with self.assertRaisesRegex(ValueError, 'missing/escaping pinned positive source'):
            probe_compiler_cli(self.compiler, self.repo)


if __name__ == '__main__':
    unittest.main()
