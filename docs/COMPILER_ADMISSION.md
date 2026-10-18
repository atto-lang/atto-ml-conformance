# Exact compiler admission for the pinned ML workspace

**Status: NO VERIFIED COMPILER ARTIFACT.** This guide is for a trusted, explicitly authorized, local three-repository workspace. No source-export permission is implied.

The Java backend's `pom.xml` identifies the Maven/Java 21 GraalVM-Truffle build; its CLI entry point is `dev.oreslang.launcher.OresMain`, which accepts a `.ores` path, `--check` and `--build-info`. The LLVM backend has a separate experimental `oreslang-llvmc` CLI. **Neither an installed Java binary nor Java/LLVM parity has been verified in this integration.** The existing launcher may not yet support the full cross-repository ML source syntax.

## Obtaining an admissible compiler executable

1. Build from a reviewed **immutable compiler source commit** in an authorized environment. Preserve build toolchain versions, exact source commit and Git tree, build logs and final binary SHA-256 as independent provenance. A host shell wrapper, Maven command name or success-marker script is **not** sufficient evidence by itself. The workspace runner does **not** invoke the provider `scripts/test.sh` wrappers as evidence, because those could produce unearned success markers without launching the compiler.
2. Place the produced compiler executable **outside the three mutable repository checkouts**; do not use a symlink to that executable. Test its real launcher independently, including `--build-info`, `--check` of an actual positive and negative `.ores` file, and an actual guest-execution probe.
3. Independently review the binary hash. Then use the exact reviewed digest:

```sh
COMPILER=/trusted/toolchains/oreslang-compiler
SHA256="$(sha256sum "$COMPILER" | awk '{print $1}')"
python3 scripts/run_workspace.py \
  --workspace /trusted/workspaces/oreslang-ml-p0 \
  --manifest manifests/p0-workspace.json \
  --compiler "$COMPILER" \
  --compiler-sha256 "$SHA256"
```

Compute the digest independently of untrusted source and compare it to the separately reviewed build attestation. Copying the value directly from a potentially malicious binary or script does **not** authenticate it.

## Fail-closed probe sequence

The runner requires a lowercase 64-hex-character SHA-256 before any guest probe. It rejects a mismatched, relative, symlinked, non-executable or source-workspace-resident compiler. It then verifies each pinned source commit and Git tree, refuses dirty checkouts, checks the complete cross-repo public-symbol/import DAG and the 14-file source-blob lock, invokes the admitted binary **directly** on six exact source files (`tests/smoke.ores` in each provider, tensor VJP smoke, and both ML autograd training examples), enforcing nonzero-exit rejection, exact one-line success output, bounded capture and timeouts, then recomputes the compiler digest to detect modification during execution.

A malicious or substituted executable could still return the expected output for every source path. Compiler-byte SHA-256 alone is identity, not provenance or semantic authenticity. Cross-repo source imports, artifact build lineage, compiler checker negative tests and numerical oracles remain distinct gates.

Even a full local success remains `EXECUTED_UNATTESTED`: exact binary hash and a marker on stdout **do not** prove source-to-binary provenance, trustworthy compiler behavior, ownership safety or Java/LLVM parity. Verify numeric results, negative semantics and backend-specific build attestation separately. Never promote the metadata-only source lock or host-only reference receipts into a compiler pass.

A source-organization Actions workflow still needs to execute real steps before generating trusted source-org evidence. Incidents [#22](https://github.com/ores-truffle-oreslang/oreslang-platform-conformance/issues/22) and [#77](https://github.com/ores-truffle-oreslang/oreslang-platform-conformance/issues/77) remain open; this procedure does **not** authorize exporting private Oreslang source to a different organization for Actions minutes.

## Additional fixture and environment controls (2026-10-18)

The direct guest runner binds **each of six** invoked `.ores` fixtures to its checked-out `HEAD:<path>` Git blob using an independent `git hash-object --no-filters` read **both before and after** that invocation. This catches modified source that `git status --porcelain` can overlook when `skip-worktree` is set. Relative paths must be canonical and stay in the verified repository Git root; symlink components and untracked fixtures are rejected. Git metadata probes ignore inherited `GIT_*` injection variables and replace/system configuration. Compiler bytes are rehashed around every invocation, and the full locked import graph plus clean workspace are revalidated after the six jobs.

The compiler is invoked with a minimal explicit environment (`PATH` fixed to the platform default, `LANG=C`, `LC_ALL=C`, `TZ=UTC`). Inherited GitHub tokens, cloud credentials, Java option injections, preload paths and `ORESLANG_BIN` are **not** forwarded. This is environment hygiene only: the process is **not sandboxed**, and an allowed executable may still access filesystem resources permitted to the calling OS account. Run it under an independently secured low-privilege OS/container identity without ambient secrets; do not infer sandboxing from SHA-256 or `RLIMIT_FSIZE`.

**Locally reproduced security tests:** 14/14 source Git-identity negatives and 10/10 direct-dispatch/env negatives passed using disposable synthetic Git histories and mock executables. These reproduce the focused admission logic, **not** a full exact-head repository checkout or Oreslang guest execution. The complete PR still requires an authorized runner with stepful checks and a reviewed, pinned real Java compiler.

**Alternate organization probe:** a no-checkout, source-free capacity workflow was staged on private `fiducia-cloud/fiducia-e2e` PR #87 (now closed unmerged). Its workflow failed before any step executed, so this probe does not establish available runner capacity. It contains no Oreslang source and does not authorize cross-org transfer. Incidents #22 and #77 remain open.


## Reconciled CLI admission and immutable guest pipeline (2026-10-18)

The stacked candidate preserves the upstream P0 source admission, exact `HEAD:<path>` guest Git blob verification, no-secret compiler environment, Git-injection defenses and post-execution import closure. It additionally requires strict `--build-info`, pinned positive `--check`, source-specific malformed negative `--check`, and repeated **commit/tree/blob/import-lock/cleanliness/compiler SHA-256** checks around each guest program. Neither source-free CI nor these preflights attest a real compiler artifact.

## Mandatory Java CLI protocol preflight (stacked integration)

The opt-in runner now calls `scripts/compiler_cli_probe.py` **after** immutable source checkout and import-closure admission, but **before** the six guest smoke programs.

- `--build-info` must return strict JSON with `build_mode`, `default_execution_mode`, and `guest_execution`, matching the Java `NativeBuildMode` contract for JVM, AOT or hybrid.
- `--check tests/smoke.ores` must succeed on the pinned Tensor source without stdout.
- `--check` on deliberately malformed synthetic `.ores` source must fail nonzero with a diagnostic and no stdout. The negative fixture is generated outside the pinned repositories.
- Compiler subprocesses use bounded output, 30-second deadlines and process-group cleanup; post-execution checks require clean source repositories and the original compiler SHA-256.

The response includes `compiler_cli_admission` with status `CLI_BEHAVIOR_PROBED_UNATTESTED`. The fifteen local shell-double tests cover denial paths and JVM/AOT/hybrid mode acceptance, **not** real Oreslang compilation or guest execution. A forged executable could still imitate the expected protocol.

The Java Maven project uses Java 21 and `dev.oreslang.launcher.OresMain` as the main class. A Maven JAR is not automatically a self-contained executable; its dependencies/module classpath must be supplied or a native image built. No exact-revision compiler artifact, independent source-to-binary attestation, or successful Oreslang ML guest run has been verified. The open private-source incidents prohibit alternate-org source mirroring without the required independent authorization.

### Hardening audit: syntax diagnostics and inter-job integrity

A generic nonzero exit is insufficient to prove a negative compile: it might be a usage error (`2`), missing dependency, crash, or unrelated stderr. The negative syntax preflight now requires exactly exit status `1`, no stdout, and a Java `OresMain`-compatible, **absolute negative fixture path plus positive line/column and `error:`** on stderr. `--build-info` also must not emit stderr. Generic errors and stdout contamination are explicitly denied. These are behavioral admissions, not compiler identity/provenance attestation.

A successful CLI probe does not permit unchecked subsequent execution. The workspace runner immediately re-verifies compiler SHA-256 and source cleanliness, and repeats both checks before and after **each** of the six guest smoke programs. The residual path-execution time-of-check/time-of-use gap and forged executable behavior remain unproven trust assumptions; approved toolchain custody and a separate attested execution environment are required for release evidence.

An independent synthetic oracle is staged at [Sagitta PR #30](https://github.com/sagitta-stack/sagitta-infra/pull/30). It contains no private source, secrets, checkout, or real compiler; its GitHub Actions receipt cannot qualify as exact-source CI or fulfill the pending protected-main security approval. The canonical cross-org publisher remains disabled while incident reviews [#22](https://github.com/ores-truffle-oreslang/oreslang-platform-conformance/issues/22) and [#77](https://github.com/ores-truffle-oreslang/oreslang-platform-conformance/issues/77) remain open.

### Exact commit/tree revalidation

Git cleanliness alone is insufficient: a compiler could use `git checkout`/`git reset` to move a provider repository to a *different clean revision* between admission and execution. `scripts/verify_pinned_checkouts.py` therefore checks all three immutable commit SHAs, Git tree SHAs and tracked/untracked cleanliness at each preflight/guest boundary. It strips caller-provided `GIT_*` environment overrides before querying Git so a poisoned `GIT_DIR`, `GIT_WORK_TREE` or `GIT_INDEX_FILE` cannot silently redirect the verifier. Seven dedicated local Git tests cover a clean HEAD change, tree mismatch, dirty/untracked files, missing provider identity, poisoned Git environment and the positive pinned case. The cumulative isolated host-only suite is **22/22**; not Oreslang guest execution.


**Integration evidence boundary:** the component-local synthetic tests were previously evaluated separately; the combined tree must pass its full suite at this exact merge head. The source-organization runner remains unable to produce a stepful proof, and cross-org source mirroring is denied while incidents #22 and #77 remain unresolved. Source-free Sagitta PR #30 may test runner capacity only.
