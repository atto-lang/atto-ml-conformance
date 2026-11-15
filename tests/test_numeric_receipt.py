import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_numeric_receipt as gate

FIXTURES = gate.read_json(ROOT / "fixtures/numeric-v1.json")


def candidate():
    return {
        "schema_version": 1,
        "backend": "rs",
        "source_sha": "a" * 40,
        "cases": [{"id": c["id"], "actual": copy.deepcopy(c["expected"])}
                  for c in FIXTURES["cases"]],
    }


class NumericReceiptTests(unittest.TestCase):
    def test_complete_candidate(self):
        self.assertEqual(gate.validate(FIXTURES, candidate()), 5)

    def test_missing_case(self):
        data = candidate()
        data["cases"].pop()
        with self.assertRaisesRegex(ValueError, "missing or extra"):
            gate.validate(FIXTURES, data)

    def test_duplicate_case(self):
        data = candidate()
        data["cases"][1] = copy.deepcopy(data["cases"][0])
        with self.assertRaisesRegex(ValueError, "duplicate reported"):
            gate.validate(FIXTURES, data)

    def test_bad_shape_and_boolean(self):
        for wrong in ([4, 1], [True, 1, 0.5]):
            data = candidate()
            data["cases"][1]["actual"] = wrong
            with self.assertRaises(ValueError):
                gate.validate(FIXTURES, data)

    def test_out_of_tolerance(self):
        data = candidate()
        data["cases"][2]["actual"] = 3.21
        with self.assertRaisesRegex(ValueError, "numeric mismatch"):
            gate.validate(FIXTURES, data)

    def test_nonfinite_and_json_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "receipt.json"
            path.write_text('{"source_sha":"a","source_sha":"b"}')
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                gate.read_json(path)
            path.write_text('{"actual":NaN}')
            with self.assertRaisesRegex(ValueError, "non-JSON numeric"):
                gate.read_json(path)
        data = candidate()
        data["cases"][0]["actual"] = float("inf")
        with self.assertRaisesRegex(ValueError, "finite JSON number"):
            gate.validate(FIXTURES, data)

    def test_malformed_provenance(self):
        for wrong in ("", "0" * 39, "Z" * 40):
            data = candidate()
            data["source_sha"] = wrong
            with self.assertRaisesRegex(ValueError, "source_sha"):
                gate.validate(FIXTURES, data)

    def test_invalid_fixture_tolerance(self):
        fixture = copy.deepcopy(FIXTURES)
        fixture["cases"][1]["abs_tol"] = -1
        with self.assertRaisesRegex(ValueError, "negative tolerance"):
            gate.validate(fixture, candidate())

    def test_reject_unknown_receipt_fields(self):
        data = candidate()
        data["verified"] = True
        with self.assertRaisesRegex(ValueError, "extended receipt"):
            gate.validate(FIXTURES, data)


if __name__ == "__main__":
    unittest.main()
