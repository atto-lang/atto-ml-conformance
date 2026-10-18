#!/usr/bin/env python3
"""Independent bounded mathematical oracle for P0 fixture data.

This checker NEVER runs the Oreslang compiler. Its success is not Oreslang
runtime conformance, cross-backend parity, or compiler provenance.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

MAX_BYTES = 131072
MAX_ELEMENTS = 10000
MAX_CASES = 100

class FixtureError(ValueError):
    pass

def no_duplicate_pairs(pairs):
    out = {}
    for key, val in pairs:
        if key in out:
            raise FixtureError("duplicate JSON object key: " + key)
        out[key] = val
    return out

def reject_nonfinite(value):
    raise FixtureError("invalid JSON numeric constant: " + value)

def load_fixture(path: Path):
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES:
        raise FixtureError("fixture exceeds bound")
    doc = json.loads(raw, object_pairs_hook=no_duplicate_pairs,
                     parse_constant=reject_nonfinite)
    if not isinstance(doc, dict) or doc.get("schema_version") != "oreslang-ml-fixtures/v1":
        raise FixtureError("unknown fixture version")
    cases = doc.get("cases")
    if not isinstance(cases, list) or not 1 <= len(cases) <= MAX_CASES:
        raise FixtureError("bad case count")
    return doc

def natural(v):
    return type(v) is int and 0 <= v <= MAX_ELEMENTS

def finite_number(v):
    return type(v) in (int, float) and math.isfinite(v)

def number_list(xs):
    if not isinstance(xs, list) or len(xs) > MAX_ELEMENTS or not all(finite_number(x) for x in xs):
        raise FixtureError("invalid numerical vector")
    return xs

def tensor(t):
    if not isinstance(t, dict) or set(t) != {"shape","values"}:
        raise FixtureError("tensor descriptor fields")
    dims = t["shape"]
    if not isinstance(dims, list) or len(dims) > 8 or not all(natural(x) for x in dims):
        raise FixtureError("invalid tensor shape")
    values = number_list(t["values"])
    size = math.prod(dims)
    if size != len(values):
        raise FixtureError("tensor shape/storage mismatch")
    return dims, values

def approx(actual, expected, atol, rtol):
    if isinstance(actual, list):
        if not isinstance(expected, list) or len(actual) != len(expected):
            raise FixtureError("expected vector length mismatch")
        for a, b in zip(actual, expected):
            approx(a, b, atol, rtol)
    else:
        if not finite_number(actual) or not finite_number(expected):
            raise FixtureError("nonfinite numeric oracle comparison")
        if abs(actual - expected) > atol + rtol * abs(expected):
            raise FixtureError(f"mismatch: actual={actual!r}, expected={expected!r}")

def compute(case):
    kind = case["kind"]
    if kind == "tensor_add":
        shape_a, a = tensor(case["left"])
        shape_b, b = tensor(case["right"])
        if shape_a != shape_b:
            raise FixtureError("add shape mismatch")
        return [x+y for x, y in zip(a, b)]
    if kind == "tensor_relu":
        _, a = tensor(case["input"])
        return [x if x > 0 else 0 for x in a]
    if kind == "tensor_sum":
        _, a = tensor(case["input"])
        return math.fsum(a)
    if kind == "tensor_matmul":
        sa, a = tensor(case["left"])
        sb, b = tensor(case["right"])
        if len(sa) != 2 or len(sb) != 2 or sa[1] != sb[0]:
            raise FixtureError("invalid matmul shape")
        m, k, n = sa[0], sa[1], sb[1]
        return [math.fsum(a[r*k+p] * b[p*n+c] for p in range(k))
                for r in range(m) for c in range(n)]
    if kind == "autograd_scalar":
        op, left, right, leaf = (case[f] for f in ("opcode","left","right","leaf_values"))
        if not all(isinstance(x, list) for x in (op,left,right,leaf)):
            raise FixtureError("invalid tape arrays")
        count = len(op)
        if not 1 <= count <= MAX_ELEMENTS or not all(len(xs) == count for xs in (left,right,leaf)):
            raise FixtureError("invalid tape count")
        values = [0.0] * count
        for i in range(count):
            if type(op[i]) is not int or op[i] not in (0,1,2):
                raise FixtureError("bad opcode")
            if op[i] == 0:
                if left[i] != -1 or right[i] != -1 or not finite_number(leaf[i]):
                    raise FixtureError("bad leaf")
                values[i] = leaf[i]
            else:
                if not all(type(p) is int and 0 <= p < i for p in (left[i],right[i])):
                    raise FixtureError("non-topological graph")
                a, b = values[left[i]], values[right[i]]
                values[i] = a+b if op[i] == 1 else a*b
        root = case["root"]
        if type(root) is not int or not 0 <= root < count:
            raise FixtureError("invalid root")
        grads = [0.0] * count
        grads[root] = 1.0
        for i in reversed(range(count)):
            if op[i] == 1:
                grads[left[i]] += grads[i]
                grads[right[i]] += grads[i]
            elif op[i] == 2:
                g = grads[i]
                grads[left[i]] += g * values[right[i]]
                grads[right[i]] += g * values[left[i]]
        return values[root], grads
    if kind == "affine_train":
        x, y = number_list(case["inputs"]), number_list(case["targets"])
        if not x or len(x) != len(y):
            raise FixtureError("invalid training shapes")
        w, b, lr = (case[k] for k in ("initial_weight","initial_bias","learning_rate"))
        steps = case["steps"]
        if not all(finite_number(v) for v in (w,b,lr)) or not 0 < lr <= 1:
            raise FixtureError("invalid hyperparameters")
        if type(steps) is not int or not 1 <= steps <= MAX_ELEMENTS:
            raise FixtureError("invalid steps")
        for _ in range(steps):
            errors = [w*xi+b-yi for xi, yi in zip(x,y)]
            gw = (2.0/len(x)) * math.fsum(e*xi for e, xi in zip(errors,x))
            gb = (2.0/len(x)) * math.fsum(errors)
            w -= lr*gw
            b -= lr*gb
        loss = math.fsum((w*xi+b-yi)**2 for xi, yi in zip(x,y))/len(x)
        return w,b,loss
    raise FixtureError("unknown case kind: " + str(kind))

def check(path):
    doc = load_fixture(path)
    tol = doc.get("tolerance")
    if not isinstance(tol, dict) or set(tol) != {"atol","rtol"}:
        raise FixtureError("invalid tolerances")
    atol, rtol = tol["atol"], tol["rtol"]
    if not all(finite_number(v) and 0 <= v <= 0.01 for v in (atol,rtol)):
        raise FixtureError("invalid tolerance bounds")
    seen = set()
    for case in doc["cases"]:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str):
            raise FixtureError("invalid case")
        if case["id"] in seen:
            raise FixtureError("duplicate case ID")
        seen.add(case["id"])
        got = compute(case)
        if case["kind"] == "autograd_scalar":
            value, grads = got
            approx(value,case["expected_value"],atol,rtol)
            approx(grads,case["expected_grads"],atol,rtol)
        elif case["kind"] == "affine_train":
            w,b,loss = got
            approx(w,case["expected_weight"],0.01,0.01)
            approx(b,case["expected_bias"],0.01,0.01)
            if not finite_number(case["max_loss"]) or loss > case["max_loss"]:
                raise FixtureError("training did not converge")
        else:
            approx(got,case["expected"],atol,rtol)
    return len(seen)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture",nargs="?",default="fixtures/p0-v1.json")
    args = parser.parse_args()
    try:
        n=check(Path(args.fixture))
    except (OSError,ValueError,KeyError,TypeError,OverflowError) as err:
        parser.exit(1,"ORACLE_FAIL: " + str(err) + "\n")
    print(f"REFERENCE_ONLY_OK cases={n}; NO_ORESLANG_BACKEND_EXECUTED")
