# Exact-SHA neural workspace and opt-in execution (2026-10-29)

This procedure is **local to an authorized environment**. No cross-org
private-repository mirroring is implied or permitted by having an Actions
budget elsewhere. Every producer checkout is independently pinned to the
exact commit and Git tree in `manifests/neural-workspace-v1.lock`.

## Checkout shape

Four checkout directories are required because the neuron prototype is based
on a *different ML feature branch* from the tensor MLP prototype:

```text
workspace/
  oreslang-tensor/       # tensor PR #13 exact commit
  oreslang-autograd/     # autograd PR #10 exact commit
  oreslang-ml/           # ML PR #23 exact commit
  oreslang-ml-neurons/   # second oreslang-ml checkout, PR #24 exact commit
```

Use local, independently authorized repo access to fetch each pinned commit.
Do **not** copy private source to alternate GitHub organizations without
independent owner authorization covering destination, retention and ACLs.
Git SHAs identify content but cannot establish transfer authorization.

Run the source-only gate:

```sh
bash scripts/verify_neural_workspace.sh /absolute/workspace
```

This rejects incorrect commit or Git tree SHA, unexpected Git root, dirty and
untracked files, symlink/submodule Git entries, actual blob content drift
(including `skip-worktree` / `assume-unchanged` masked modifications), or
missing source. It checks **every** tracked blob. It does NOT verify the compiler,
execute any `.ores` program or prove network provenance.

Source-free adversarial verification can run separately:

```sh
bash tests_sh/verify_neural_workspace.test.sh
```

This creates disposable synthetic Git repositories only. It never accesses
or mirrors any private provider content and cannot be represented as a compiler
or runtime test.

## Native guest gate after compiler integration

Build an independently reviewed and pinned Oreslang compiler using the
appropriate backend (Java 25/GraalVM and LLVM independently). Capture full
source Git commit/tree and toolchain/binary provenance before invoking it.
On a trusted **Linux** runner with timeout/sha256sum/git/bash, execute:

```sh
bash scripts/run_neural_native_guests.sh \
  /absolute/workspace \
  /absolute/reviewed/oreslang-compiler \
  0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
```

Replace the final example value with the actual externally verified SHA-256
of the executable, **not** a made-up digest. The script checks it before and
after every guest and re-verifies all four pinned trees around each run. It
requires exactly these five actual Oreslang stdout markers:

| Source | Expected stdout |
| --- | --- |
| `oreslang-tensor/tests/conv1d_vjp_smoke.ores` | `ORES_TENSOR_CONV1D_VJP_PASS` |
| `oreslang-autograd/examples/tensor_training_vjp_smoke.ores` | `ORES_AUTOGRAD_TENSOR_TRAINING_VJP_PASS` |
| `oreslang-ml/examples/train_tensor_mlp_vjp_cpu.ores` | `ORES_ML_TENSOR_TWO_LAYER_VJP_PASS` |
| `oreslang-ml/examples/train_adamw_smoke.ores` | `ORES_ML_ADAMW_CHECKED_PASS` |
| `oreslang-ml-neurons/examples/train_stateful_neuron_microprocs.ores` | `ORES_ML_STATEFUL_NEURON_BACKPROP_PASS` |

All output is bounded, timeouts fail closed, and unexpected output or nonzero
exit rejects the suite. **Even success is `EXECUTED_UNATTESTED`**, not
`VERIFIED_BACKEND`: success markers can be forged by a fake executable.
Independent compiler binary provenance, actual captured command and stdout,
guest worker restrictions, reviewed dynamic imports, release safety cases and
verified CI nonzero steps are required for promotion. This shell runner cannot
prevent a hostile compiler from reading local secrets or source and is NOT an
execution sandbox. Only run it in a hardened, credential-free sandbox.

Current known blockers:
- Actor `handle_state` sealed callback return semantics are not fully
  integrated in the Java compiler mainline (Java PRs #1804/#1806/#760).
- Tensor storage is still provisional `List<float>`, not compiler-proven
  unique `Array<T>` or frozen activation leases.
- The separate native guest acceptance scripts have not produced verified
  Java/LLVM receipts; new private Actions runs failed with **zero job steps**.
- An individual Conv1D operator, numerical MLP and two-neuron demonstration
  do not establish full CNN, transformer, KAN or distributed ML support.

## Gate ordering

1. `SOURCE_ONLY`: pinned SHAs + every Git blob pass, local files unmodified.
2. `REFERENCE_ONLY`: independent Rust numeric oracles pass **if actually run**.
3. `EXECUTED_UNATTESTED`: compiler binary hash and exact stdout/exit checks.
4. `VERIFIED_BACKEND`: independently attest compiler source-to-binary,
   untrusted-input guards, matching guest semantics and stepful CI.
5. Multi-backend parity: compare independently verified Java, LLVM, WASM,
   Forge, .NET and Cranelift results, separately recording unsupported cases.

The lock file MUST be explicitly reviewed and repinned if any producer PR
moves. Never follow floating PR heads during a trusted acceptance run.
