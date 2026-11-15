#!/usr/bin/env python3
"""Fail-closed structural/numeric checker for *candidate* backend receipts.

No test here invokes or authenticates an Atto guest compiler/runtime.
"""
import argparse
import json
import math
from pathlib import Path
import re
import sys

BACKENDS = frozenset(("rs", "java", "llvm", "wasm", "forge", "net", "js", "cranelift"))
MAX_JSON_BYTES = 1_048_576
MAX_CASES = 128
MAX_DEPTH = 8


def _no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f"non-JSON numeric constant: {value}")


def read_json(path):
    path = Path(path)
    if path.stat().st_size > MAX_JSON_BYTES:
        raise ValueError("JSON file exceeds 1 MiB")
    return json.loads(path.read_text(encoding="utf-8"),
                      object_pairs_hook=_no_duplicates,
                      parse_constant=_reject_constant)


def _check_number(value, name):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{name}: expected finite JSON number")
    return value


def _compare(expected, actual, abs_tol, rel_tol, path, depth=0):
    if depth >= MAX_DEPTH:
        raise ValueError(f"{path}: numeric nesting exceeds limit")
    if type(expected) is list:
        if type(actual) is not list or len(expected) != len(actual):
            raise ValueError(f"{path}: result shape mismatch")
        for index, (left, right) in enumerate(zip(expected, actual)):
            _compare(left, right, abs_tol, rel_tol, f"{path}[{index}]", depth + 1)
        return
    left = _check_number(expected, path + " expected")
    right = _check_number(actual, path + " actual")
    if not math.isclose(left, right, abs_tol=abs_tol, rel_tol=rel_tol):
        raise ValueError(f"{path}: numeric mismatch")


def validate(fixtures, receipt):
    if type(fixtures) is not dict or fixtures.get("schema_version") != 1:
        raise ValueError("unsupported fixture schema")
    cases = fixtures.get("cases")
    if type(cases) is not list or not (1 <= len(cases) <= MAX_CASES):
        raise ValueError("fixture case count out of range")
    expected = {}
    for case in cases:
        if type(case) is not dict or type(case.get("id")) is not str:
            raise ValueError("malformed fixture case")
        case_id = case["id"]
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", case_id) or case_id in expected:
            raise ValueError("invalid or duplicate fixture ID")
        if "expected" not in case:
            raise ValueError(f"{case_id}: missing expected result")
        abs_tol = _check_number(case.get("abs_tol", 0), case_id + " abs_tol")
        rel_tol = _check_number(case.get("rel_tol", 0), case_id + " rel_tol")
        if abs_tol < 0 or rel_tol < 0:
            raise ValueError(f"{case_id}: negative tolerance")
        expected[case_id] = (case["expected"], abs_tol, rel_tol)

    if type(receipt) is not dict or set(receipt) != {
        "schema_version", "backend", "source_sha", "cases"
    }:
        raise ValueError("malformed or extended receipt fields")
    if type(receipt["schema_version"]) is not int or receipt["schema_version"] != 1:
        raise ValueError("unsupported receipt schema")
    if receipt["backend"] not in BACKENDS:
        raise ValueError("unknown backend identifier")
    sha = receipt["source_sha"]
    if type(sha) is not str or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("source_sha must be a lowercase 40-hex Git commit")
    reported = receipt["cases"]
    if type(reported) is not list or len(reported) != len(expected):
        raise ValueError("missing or extra case entries")
    seen = set()
    for entry in reported:
        if type(entry) is not dict or set(entry) != {"id", "actual"}:
            raise ValueError("malformed reported case")
        case_id = entry["id"]
        if type(case_id) is not str or case_id in seen or case_id not in expected:
            raise ValueError("unknown or duplicate reported case")
        seen.add(case_id)
        value, abs_tol, rel_tol = expected[case_id]
        _compare(value, entry["actual"], abs_tol, rel_tol, case_id)
    if seen != set(expected):
        raise ValueError("incomplete case set")
    return len(seen)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", default=str(Path(__file__).resolve().parents[1] /
                                                    "fixtures/numeric-v1.json"))
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)
    try:
        count = validate(read_json(args.fixtures), read_json(args.receipt))
    except (ValueError, OSError, TypeError, OverflowError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: {count} candidate numeric results; NOT guest execution attestation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
