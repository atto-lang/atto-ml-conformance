# Neural training validation — evidence and promotion matrix

This is the **reference-only** numerical expansion for the actor-native ML
program. It does not assert actual execution of a single Oreslang source file.
Keep the producer PRs and this branch in draft until native receipts exist.

## Exact source dependencies

| Producer | New draft source |
| --- | --- |
| Autograd | oreslang-autograd PR #10, `src/tensor_training_vjp.ores` |
| Tensor | oreslang-tensor PR #13, `src/conv1d.ores` |
| ML | oreslang-ml PR #23, `examples/train_tensor_mlp_vjp_cpu.ores`, `src/adamw.ores` |
| Actor demo | oreslang-ml PR #24, `examples/train_stateful_neuron_microprocs.ores` |

These PRs have **different parent feature branches**. An integration
workspace must use an exact manifest of checked out producer SHAs,
not blindly assume that main contains any of the new files.

## Independent Rust oracle

`tests_rust/neural_vjp_oracle.rs` requires only Rust's standard library.
It checks:
- ReLU VJP versus finite differences away from the zero kink;
- MSE mean-reduction gradient versus finite differences;
- 1D convolution signal/filter VJPs versus independent central differences;
- all seven parameters of the 1->2->1 ReLU MLP against finite differences;
- deterministic 600-step mini-MLP SGD loss convergence;
- first-step bias-corrected AdamW with decoupled weight decay;
- two persistent-neuron gradient chain and a stale/replay reference model.

Run with `rustc --edition=2021 --test -D warnings
tests_rust/neural_vjp_oracle.rs -o /tmp/ores-ml-neural-vjp && 
/tmp/ores-ml-neural-vjp` (use a local temporary output path). The source-org
`neural-vjp-oracle.yml` workflow runs the same standard-library tests.
It never downloads private source across organizational boundaries.

Even a clean successful Rust host run means only `REFERENCE_ONLY`.
There is no implied correctness of the actual `.ores` program or compiler.

## Separate backend receipts required

| Backend | Native guest gate | Status until executed |
| --- | --- | --- |
| Java/GraalVM | pinned Java 25/Graal compiler, full `.ores` typecheck and execution, stdout oracle | NOT VERIFIED |
| LLVM | compiler source hash, native AOT binary, exit/stdout, sanitizers and ownership negatives | NOT VERIFIED |
| WASM | sandboxed worker execution plus value/shape/error identity | NOT VERIFIED |
| Forge | JIT/AOT guest execution and effect-safe graph optimization equivalence | NOT VERIFIED |
| .NET | native AOT guest execution, no JIT fallback | NOT VERIFIED |
| Cranelift | independent compiler/runtime execution when supported | NOT VERIFIED |

For every positive guest: include compiler source+binary identity, exact
producer Git commits/trees, dependency lock, command, toolchain, stdout,
stderr, exit code and nonzero CI job steps. For every negative guest:
shape mismatch, alias escape, nonfinite, duplicate/stale gradient, restart ABA,
cross-tenant capability spoof, cancellation and unauthorized CONTROL.

**Prohibited evidence inflation:** `NO_STEPS` is runner-admission failure;
`REFERENCE_ONLY` is not guest execution; `EXECUTED_UNATTESTED` is not
`VERIFIED_BACKEND`. A source-only regex check, JS or Rust oracle and a
simulator GPU receipt cannot promote a backend. Do not transfer private source
to another GitHub organization solely to use spare CI minutes without
independent source-owner authorization and governance approval.

## Outstanding implementation blockers

- Generic reverse-mode graph/tape with tensor operation leases and topological
  fan-in. Individual VJPs are not the complete tape.
- Unique contiguous `Array<T>`, checked offsets/strides and saved generation
  pinning; current `List<float>` guards are a semantic reference.
- The canonical sealed actor-state compiler implementation and callback return
  semantics, plus supervised restart/capability CONTROL.
- CNN Conv2D/pooled layers; numerically stable softmax and attention VJP;
  transformer blocks; general KAN integration using existing PR #19;
  generalized MLP dimensions and complete stable optimizer state.
- Real source-org runner admission with executed steps and compiler-backed
  Java/LLVM evidence; all later backends reported independently.
