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

## Candidate numeric receipt validation (preview)

The versioned `fixtures/numeric-v1.json` contains scalar, vector, dot, matrix multiplication and reduction cases. Validate a backend's claimed output with `python tools/check_numeric_receipt.py --receipt path/to/receipt.json` (schema: `schema_version`, `backend`, `source_sha`, `cases: [{id, actual}]`). Malformed, duplicate, non-finite, missing, extra, or out-of-tolerance outputs fail closed. `python -m unittest discover -s tests -v` runs host-only negative tests.

**Evidence boundary:** This checker compares a candidate receipt to deterministic fixtures; it does not run a compiler, prove execution, attest provenance, or establish any backend conformance. Backend adapters must supply independent exact-source executed-guest evidence before a PASS can be considered language parity.
