"""Test the reference fixture validator; NOT guest Oreslang execution."""
import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_reference import check, FixtureError

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/p0-v1.json"

class ReferenceTests(unittest.TestCase):
    def test_golden(self):
        self.assertEqual(check(FIXTURE), 6)

    def test_tampered_expected_rejected(self):
        doc = json.loads(FIXTURE.read_text())
        doc["cases"][0]["expected"][0] += 100
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/"bad.json"
            path.write_text(json.dumps(doc))
            with self.assertRaises(FixtureError):
                check(path)

    def test_unknown_case_rejected(self):
        doc = json.loads(FIXTURE.read_text())
        doc["cases"][0]["kind"] = "host_side_magic"
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/"bad.json"
            path.write_text(json.dumps(doc))
            with self.assertRaises(FixtureError):
                check(path)

    def test_duplicate_json_key_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/"bad.json"
            path.write_text('{"schema_version":"oreslang-ml-fixtures/v1","cases":[],"cases":[]}')
            with self.assertRaises(FixtureError):
                check(path)

    def test_boolean_is_not_numeric(self):
        doc = json.loads(FIXTURE.read_text())
        doc["cases"][0]["left"]["values"][0] = True
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/"bad.json"
            path.write_text(json.dumps(doc))
            with self.assertRaises(FixtureError):
                check(path)

if __name__ == "__main__":
    unittest.main()
