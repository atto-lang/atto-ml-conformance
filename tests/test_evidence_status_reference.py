"""Minimal fail-closed evidence *classification* gate (not an attestor).
No self-reported receipt or reference oracle can be VERIFIED_BACKEND.
"""
import re
import unittest

BACKENDS = ("java", "llvm", "wasm", "forge", "net")
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")

def classify(report):
    if type(report) is not dict or report.get("backend") not in BACKENDS:
        raise ValueError("unknown backend/receipt")
    if report.get("supported") is not True:
        return "REFERENCE_ONLY"
    steps = report.get("executed_steps")
    if type(steps) is not int or steps < 0 or steps > 100000:
        raise ValueError("invalid step count")
    if steps == 0:
        return "NO_STEPS"
    if not SHA40.fullmatch(report.get("checkout_sha", "")):
        raise ValueError("missing exact checkout identity")
    if not SHA64.fullmatch(report.get("compiler_binary_sha256", "")):
        raise ValueError("missing compiler binary digest")
    if not SHA64.fullmatch(report.get("guest_source_sha256", "")):
        raise ValueError("missing guest source digest")
    if report.get("guest_exit") != 0 or report.get("timeout") is not False:
        return "EXECUTED_UNATTESTED"
    if report.get("tests_passed") is not True or report.get("tests_skipped") != 0:
        return "EXECUTED_UNATTESTED"
    # Integrity of fields is not independent authentication of source-to-binary.
    # Separate trusted builder, immutably pinned provenance and reviewer needed.
    return "EXECUTED_UNATTESTED"

class EvidenceGateTests(unittest.TestCase):
    def setUp(self):
        self.good = dict(backend="java", supported=True, executed_steps=3,
                         checkout_sha="a"*40, compiler_binary_sha256="b"*64,
                         guest_source_sha256="c"*64, guest_exit=0,
                         timeout=False, tests_passed=True, tests_skipped=0)
    def test_never_promotes_unattested_execution(self):
        for backend in BACKENDS:
            self.assertEqual(classify({**self.good, "backend": backend}),
                             "EXECUTED_UNATTESTED")
    def test_zero_step_is_not_test_failure_or_success(self):
        self.assertEqual(classify({**self.good, "executed_steps": 0}),"NO_STEPS")
    def test_unsupported_is_not_passing(self):
        self.assertEqual(classify({**self.good, "supported": False}),"REFERENCE_ONLY")
    def test_missing_digests_and_fake_steps_fail_closed(self):
        for change in ({"executed_steps":True},{"executed_steps":-1},
                       {"checkout_sha":"z"*40},{"compiler_binary_sha256":"b"},
                       {"guest_source_sha256":"c"*40}):
            with self.assertRaises(ValueError):
                classify({**self.good, **change})
    def test_skips_and_runtime_failure_cannot_upgrade(self):
        for change in ({"tests_skipped":1},{"guest_exit":1},
                       {"timeout":True},{"tests_passed":False}):
            self.assertEqual(classify({**self.good,**change}),"EXECUTED_UNATTESTED")

if __name__=="__main__":
    unittest.main()
