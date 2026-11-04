# Neural integration source-only test evidence — 2026-10-29

**Classification: SOURCE_ONLY / REFERENCE_INFRASTRUCTURE.**
This is NOT an Oreslang compiler, ML model, real actor runtime, Java/LLVM,
Rust numerical oracle or verified backend execution receipt.

## Independently checked exact Git blob identities

Four scripts were reconstituted in an isolated local test workspace, and their
raw content was checked with `git hash-object` against the current exact GitHub
blob identities in conformance PR #13:

| Tested file | Git blob SHA-1 |
| --- | --- |
| `scripts/verify_neural_workspace.sh` | `7e48442bb47d1787e3a4c1b0b1197a9a76bd8817` |
| `tests_sh/verify_neural_workspace.test.sh` | `1aace5efc56c763755acb62f0fd4febeb02a8d66` |
| `scripts/run_neural_native_guests.sh` | `0acc43e2c8fc39804243c039c5dff03ca8f94cae` |
| `tests_sh/run_neural_native_guests.test.sh` | `feaaee2e21cfbe3930fc3bbfcd44a2e14d445486` |

These are Git content-addressed blobs, not a provenance attestation of the
test host. They must be rechecked after any content change.

## Actual local source-free executions

Environment: Linux, Git 2.47.3, GNU Bash 5.2.37, GNU coreutils
(`sha256sum`) 9.7.

- `bash -n scripts/verify_neural_workspace.sh` — exit 0.
- `bash -n tests_sh/verify_neural_workspace.test.sh` — exit 0.
- `bash tests_sh/verify_neural_workspace.test.sh` — exit 0,
  `NEURAL_SOURCE_LOCK_NEGATIVES_PASS`.
- `bash -n scripts/run_neural_native_guests.sh` — exit 0.
- `bash -n tests_sh/run_neural_native_guests.test.sh` — exit 0.
- `bash tests_sh/run_neural_native_guests.test.sh` — exit 0,
  `NEURAL_NATIVE_GATE_SYNTHETIC_NEGATIVES_PASS`.

Negative input cases actually exercised: clean 4-checkout source admission;
dirty files; `skip-worktree` and `assume-unchanged` index masking;
untracked/staged symlink; incorrect pinned Git tree; fake compiler with
correct markers **must** remain `EXECUTED_UNATTESTED`; mismatching SHA-256;
unexpected guest stdout; and fake compiler mutation of source after output.

Separate single-repository, source-free Git test also reproduced that a
`skip-worktree` mutation leaves `git status --porcelain` empty but changes
`git hash-object --no-filters` relative to HEAD.

## Not performed or claimed

- No real `.ores` program was parsed, compiled, typechecked or executed.
- No Rust numerical oracle binary was compiled/executed in the local host.
- No GraalVM 25/LLVM source-to-binary receipt, LLVM sanitizer, GPU device,
  actor restart, or multi-backend result exists from this test.
- GitHub Actions source-org jobs for the conformance PR at previous exact
  head `702a140d26a0985a3bd865f2b1aded4de8e0c60a` failed with **zero
  job steps**. New commits need independently checked head-specific runs.
- Neither the source-only verifier nor the native guest wrapper is an
  authorization to transfer private code across GitHub organizations.
- A malicious fake compiler can emit expected stdout; the native guest wrapper
  deliberately reports `EXECUTED_UNATTESTED`, never `VERIFIED_BACKEND`.

Next admissible promotion: independently approved trusted runner with nonzero
steps, exact producer commits/trees and compiler binary build provenance,
real Java/Graal and LLVM guest execution, and independent finite-difference
oracles. Reconciliation of Java actor state loan return semantics remains a
separate P0 dependency in Java issue #1349 and PRs #1804/#1806/#760.
