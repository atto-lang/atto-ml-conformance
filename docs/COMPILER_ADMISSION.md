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
