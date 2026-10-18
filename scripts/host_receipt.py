#!/usr/bin/env python3
"""Write a narrow host-only CI receipt. Never certifies Oreslang guest execution."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

SCHEMA = "oreslang-ml-host-reference-receipt/v1"


def parse_node_summary(log):
    values = {}
    for field in ("tests", "pass", "fail", "skipped", "todo", "cancelled"):
        matches = re.findall(r"(?m)^# " + field + r" (\d+)\s*$", log)
        if len(matches) > 1 or (field in ("tests", "pass", "fail") and len(matches) != 1):
            raise ValueError("ambiguous or missing Node test summary: " + field)
        values[field] = int(matches[0]) if matches else 0
    if (values["tests"] < 1 or values["pass"] != values["tests"] or
            any(values[k] != 0 for k in ("fail", "skipped", "todo", "cancelled"))):
        raise ValueError("Node tests did not all pass without skips")
    return values["tests"]


def parse_python_summary(log):
    counts = re.findall(r"(?m)^Ran (\d+) tests? in [^\n]+$", log)
    ok = re.findall(r"(?m)^OK\s*$", log)
    if len(counts) != 1 or int(counts[0]) < 1 or len(ok) != 1 or "FAILED" in log:
        raise ValueError("ambiguous or failed Python unittest summary")
    return int(counts[0])


def make_receipt(expected, observed, tree, node, python_tests, reference_marker):
    if not all(re.fullmatch(r"[a-f0-9]{40}", x or "") for x in (expected, observed, tree)):
        raise ValueError("invalid Git object identity")
    if observed != expected:
        raise ValueError("checked-out commit differs from event head")
    if reference_marker != "REFERENCE_PASS\n":
        raise ValueError("independent Python reference check missing")
    return {"schema": SCHEMA, "source_commit": observed, "source_git_tree": tree,
            "node_host_tests_passed": parse_node_summary(node),
            "python_host_tests_passed": parse_python_summary(python_tests),
            "python_reference_passed": True,
            "node_log_sha256": hashlib.sha256(node.encode()).hexdigest(),
            "python_log_sha256": hashlib.sha256(python_tests.encode()).hexdigest(),
            "source_export_authorized": False, "private_source_transferred": False,
            "native_compiler_executed": False, "native_guest_executed": False,
            "release_ready": False, "evidence_scope": "HOST_REFERENCE_ONLY"}


def main():
    p = argparse.ArgumentParser()
    for name in ("expected-sha", "node-log", "python-log", "reference-marker", "output"):
        p.add_argument("--" + name, required=True)
    args = p.parse_args()
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, timeout=10, check=True).stdout.strip()
    tree = subprocess.run(["git", "rev-parse", "HEAD^{tree}"], capture_output=True,
                          text=True, timeout=10, check=True).stdout.strip()
    receipt = make_receipt(args.expected_sha, head, tree,
                           Path(args.node_log).read_text(), Path(args.python_log).read_text(),
                           Path(args.reference_marker).read_text())
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print("HOST_REFERENCE_RECEIPT_ONLY commit=" + head)


if __name__ == "__main__":
    main()
