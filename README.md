> **AI agent instructions (organization-wide):** Before working on code, issues, or pull requests, read and follow the [organization `AGENTS.md`](https://github.com/atto-lang/.github/blob/main/AGENTS.md), including its **merge-first stealth-development policy**. Honor any repository-local `AGENTS.md`, explicit holds, and GitHub-enforced rules.

# atto-ml-conformance

Cross-backend conformance tests for AttoLang machine-learning and numerical functionality.

## Naming migration and language authority

This repository is maintained at [atto-lang/atto-ml-conformance](https://github.com/atto-lang/atto-ml-conformance); use `https://github.com/atto-lang/atto-ml-conformance.git` for Git remotes and canonical `.atto` source examples. The normative language contract is [atto-spec](https://github.com/atto-lang/atto-spec), with executable guest evidence tracked by [atto-platform-conformance](https://github.com/atto-lang/atto-platform-conformance). Follow current ownership, borrowing, effects, actor, and syntax rules there; do not infer implemented features from a README or unexecuted CI.

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

AttoLang is the canonical project name; new source, examples and documentation use `.atto` and the `atto-lang` repository organization. This README defines scope, not feature readiness.

**Acceptance:** name exact source SHA/tree, runtime/toolchain, positive and negative checks and execution receipt before claiming support. Host-only tests and empty CI steps do not prove guest execution.

## Numerical conformance reference (host-only)

`reference/numeric_oracle.py` defines finite scalar comparison with configurable nonnegative absolute and relative tolerances, explicit size budgeting, first-class mismatch indices, and a separate strict guest metadata admission helper. Run `python3 -m unittest discover -s tests -v` to check example pass/fail/negative cases.

The comparator produces **host reference results only**. A digest-bearing guest metadata record is not proof of a real Atto execution; independent artifact/runner verification and exact target precision must be added before claiming ML/backend parity. This initial oracle does not support NaN equivalence, tensors with differing shapes, signed overflow, or nondeterministic reductions.

The host oracle rejects integers too large to represent as finite floats instead of leaking Python `OverflowError`; a future Atto integer-exact comparison oracle requires a separate non-floating-point contract.
