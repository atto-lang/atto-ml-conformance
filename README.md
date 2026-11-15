# atto-ml-conformance

Cross-backend conformance tests for AttoLang machine-learning and numerical functionality.

## Purpose

Validate tensor/numerical contracts, supported operations, and backend-specific availability.

## Repository responsibilities

- Keep interfaces, schemas, and behavior documented in a backend-neutral form where applicable.
- Use test fixtures and reproducible evidence to distinguish proposed behavior from implemented behavior.
- Record breaking changes, migration notes, and dependencies on other AttoLang components.

## Validation

Validation should rely on checked-in tests and exact-commit CI results. When reporting parity, distinguish **passed**, **failed**, **unsupported**, and **not executed**. Avoid inferring guest-runtime support from host-only tests.

## Status and development

This README records the intended role of this repository; it is not a claim of feature completeness. Consult the source tree and workflow files for actual implementation and verified build commands. Contributions should preserve compatibility with the canonical language contract.

## Ecosystem

- [AttoLang](https://github.com/atto-lang)
- [Language specification](https://github.com/atto-lang/atto-spec)
- [Cross-platform conformance](https://github.com/atto-lang/atto-platform-conformance)

## Repository ownership and contribution routing

**Belongs here:** Shared numerical/ML fixtures, numerical tolerances, backend coverage matrix and portable model/tensor behavior receipts.

**Belongs elsewhere:** ML features belong in atto-ml/atto-tensor/atto-autograd; general language compliance in atto-platform-conformance.

**Security and portability boundary:** Report actual guest execution, target precision, deterministic settings and tolerances; do not confuse host Rust/Python reference results with AttoLang backend execution.

AttoLang is the public name; preserve existing Oreslang/.ores compatibility and use canonical .atto for new portable library source. This README defines scope, not feature readiness.

**Acceptance:** name exact source SHA/tree, runtime/toolchain, positive and negative checks and execution receipt before claiming support. Host-only tests and empty CI steps do not prove guest execution.

## Numerical conformance reference (host-only)

`reference/numeric_oracle.py` defines finite scalar comparison with configurable nonnegative absolute and relative tolerances, explicit size budgeting, first-class mismatch indices, and a separate strict guest metadata admission helper. Run `python3 -m unittest discover -s tests -v` to check example pass/fail/negative cases.

The comparator produces **host reference results only**. A digest-bearing guest metadata record is not proof of a real Atto execution; independent artifact/runner verification and exact target precision must be added before claiming ML/backend parity. This initial oracle does not support NaN equivalence, tensors with differing shapes, signed overflow, or nondeterministic reductions.
