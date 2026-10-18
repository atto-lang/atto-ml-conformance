# Exact compiler admission for the pinned ML workspace

**Status: NO VERIFIED COMPILER ARTIFACT.** This guide is for a trusted, explicitly authorized, local three-repository workspace. No source-export permission is implied.

The Java backend's `pom.xml` identifies the Maven/Java 21 GraalVM-Truffle build; its CLI entry point is `dev.oreslang.launcher.OresMain`, which accepts a `.ores` path, `--check` and `--build-info`. The LLVM backend has a separate experimental `oreslang-llvmc` CLI. **Neither an installed Java binary nor Java/LLVM parity has been verified in this integration.** The existing launcher may not yet support the full cross-repository ML source syntax.

## Obtaining an admissible compiler executable

1. Build from a reviewed **immutable compiler source commit** in an authorized environment. Preserve build toolchain versions, exact source commit and Git tree, build logs and final binary SHA-256 as independent provenance. A host shell wrapper, Maven command name or success-marker script is **not** sufficient evidence by itself.
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

The runner requires a lowercase 64-hex-character SHA-256 before any guest probe. It rejects a mismatched, relative, symlinked, non-executable or source-workspace-resident compiler. It then verifies each pinned source commit and Git tree, refuses dirty checkouts, checks the complete cross-repo public-symbol/import DAG and the 14-file source-blob lock, executes the six pinned smoke programs with captured bounded output and timeouts, then recomputes the compiler digest to detect modification during execution.

Even a full local success remains `EXECUTED_UNATTESTED`: exact binary hash and a marker on stdout **do not** prove source-to-binary provenance, trustworthy compiler behavior, ownership safety or Java/LLVM parity. Verify numeric results, negative semantics and backend-specific build attestation separately. Never promote the metadata-only source lock or host-only reference receipts into a compiler pass.

A source-organization Actions workflow still needs to execute real steps before generating trusted source-org evidence. Incidents [#22](https://github.com/ores-truffle-oreslang/oreslang-platform-conformance/issues/22) and [#77](https://github.com/ores-truffle-oreslang/oreslang-platform-conformance/issues/77) remain open; this procedure does **not** authorize exporting private Oreslang source to a different organization for Actions minutes.

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
