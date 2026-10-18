# Oreslang ML program contract — M1–M6

Status: architecture and acceptance criteria tracked; **not** a claim that PyTorch/TensorFlow parity is complete.

## Non-negotiable boundaries

1. Pure Oreslang owns all user-facing numerical algorithms, tensors, VJP/JVP, layers, optimizers, training loops, and model implementations. Host libraries are external test oracles only.
2. One logical `Tensor<T>` API under both immediate eager evaluation and captured compiled execution. No independent language frontend in the ML graph compiler.
3. Reuse `oreslang-data-science` for the common `NdArray<T>`, shapes, and numerical kernels; ML tensors add autodiff, device and metadata semantics rather than maintaining a conflicting ndarray runtime.
4. `oreslang-common-source` defines language-level ownership/effects/HIR/MIR and lowering contracts, not ML-specific graph optimizations. LLVM and Java/Graal implement identical source semantics or report unsupported explicitly.
5. Bare-metal `core` remains OS/libc/allocator-free. Tensor allocation is opt-in via `alloc`; CPU threads, devices, filesystems, drivers, and OTP are optional capability-bearing layers. No mandatory JVM/OS requirements leak into `core`.
6. Tensor compute is DOP kernels, **not one actor per tensor/layer**. Actors own orchestration, workers, data loading, checkpoints and supervision; concurrency >1 still requires explicit parameter ownership and synchronization.

## Source ownership and targets

| Layer | Repo owner | Near-term proof | Current admission |
| --- | --- | --- | --- |
| Numeric foundation | `oreslang-data-science`, `oreslang-tensor` | contiguous f64 CPU ndarray/tensor, 0D–ND, shape algebra, broadcast, strided views, matmul, reductions | `List<float>` reference algorithms only; compiler ownership pending |
| Reverse autodiff | `oreslang-autograd` | topological tape, add/mul/ReLU, tensor VJP incl. unbroadcast, checked saved generations | scalar tape implemented in draft, not compiler-proven |
| Deep learning | `oreslang-ml` | Linear/ReLU/Sequential/MSE/SGD, two-layer end-to-end training; Adam/AdamW next | analytic affine and scalar-autograd MLP examples committed, not executable evidence |
| Graph compiler | `oreslang-ml-compiler` **future P1** | typed ML IR, eager/compiled equivalence, constant folding, fusion, shape specialization, effect/alias barriers | repo not yet created; do not claim implemented |
| Accelerators | `oreslang-ml-accelerators` **future P1** | CPU SIMD/multicore; one real hardware GPU backend, transfers and explicit no-fallback | repo not yet created; no physical GPU evidence |
| AI ecosystem | `oreslang-ml-models`, `oreslang-ml-distributed`, `oreslang-ml-serving` **future P2** | transformer model, ONNX/Safetensors, actor supervision, batching, scale tests | deferred until P0+P1 gates |

Supporting repos: `oreslang-source.java` (reference compiler), `oreslang-source.llvm` (native AOT),
`oreslang-common-source` (language semantics), `oreslang-target-profiles` (device capabilities),
`oreslang-platform-conformance` (cross-backend evidence), `oreslang-hpc-finance` (numeric benchmarks),
`oreslang-serialization-and-validation` (formats/Zorde), `oreslang-otel` (observability).

## M1. CPU numerical foundation

- `Tensor<T>`: dtype, device, shape, strides, offset, storage, layout, lifetime/ownership.
- Rank zero and zero-extent semantics; f32/f64, shape-product overflow, negative dimensions, endian/layout/bit widths explicitly specified.
- Broadcasting, reshape, transpose, slice/view, contiguous/noncontiguous storage, elementwise/reductions/matmul.
- Each operation has positive, negative, aliasing, overflow/NaN, and shape tests.
- Compiler-enforced unique mutable ownership, pinned nonescaping borrows, generation IDs for view invalidation; explicit device leases for async.
- Per-target explicit support matrix; no JVM acceptance promoted to LLVM native AOT without exact-head compilation and execution.
- Release gate: native compiler executes tensor fixture suite and NdArray sharing is proven.

## M2. Autograd

- Reverse mode add/sub/mul/div/matmul/sum/mean/reshape/transpose/ReLU/sigmoid/tanh/softmax/cross-entropy, including broadcast-to-original gradient reduction.
- A single eager recorder and graph representation with node generations; prohibit mutation of any saved activation while borrowed.
- Gradient accumulation on fan-out DAG, deterministic execution and defined ReLU subgradient at zero.
- Finite difference, analytic fixture and independently implemented differential oracle for each VJP; error semantics for nonfinite intermediates and cancellation.
- Later: JVP, VJP composition, Jacobians, higher-order gradients and checkpointing.
- Release gate: real `.ores` compiler executes tensor gradients with all three independent oracles; no stale tensor can produce a gradient.

## M3. Deep learning

- Pure `.ores` `nn/{module,linear,sequential,activation,normalization,loss}`,
  `optim/{sgd,adam,adamw}`, `training/{trainer,gradients,checkpoint}`,
  `data/{dataset,dataloader}` and `metrics/{accuracy,loss}`.
- Fixed-seed CPU two-layer MLP, reproducible training and validation loss; MNIST then attention/transformer workloads.
- Explicit owner for mutable parameters/optimizer state. Actor concurrency cannot cause unsynchronized weight races.
- Release gate: end-to-end two-layer **tensor** MLP uses generic autograd, not manually differentiated affine reference.

## M4. ML graph compiler

- First define typed ML IR with shape, dtype, alias, regions, device, effects and operation identity; make eager capture semantics identical.
- Prove value/effect preservation for constant folding, DCE, fusion, specialization, tiling and vectorization; unsafe FP reassociation requires opt-in mode.
- AOT artifact metadata includes target profile and source/toolchain hashes; compare eager vs captured vs compiled output.
- Lower through existing LLVM compiler; MLIR/StableHLO interop is versioned and tested, not a new language frontend.
- Release gate: identical `.ores` model runs through eager and native AOT compiled graph within declared tolerances.

## M5. Hardware and distributed execution

- CPU scalar first, SIMD/multicore second, one physical GPU backend third, then NVIDIA/AMD/Metal/Vulkan as independent targets.
- Explicit GPU device selection must fail rather than silently switch to CPU. Device allocator, streams, errors and transfers carry owned generation leases.
- Cancellation and worker failure must release buffers, supervisor events and partial checkpoints coherently.
- Actors coordinate data pipelines, gradient aggregation/sharding, worker supervision and observability, not per-element math.
- Release gate: physical GPU stepful CI with device name/profile, complete source identity and measured correctness/performance, never simulator-only evidence.

## M6. Interchange and ecosystem

- Safetensors for bounded data-only weights; ONNX opset/IR checks and stable graph semantics; StableHLO for compiler interoperability.
- Checkpoint and tensor metadata represented as independently authored TypeSpec + Draft 2020-12 JSON Schema peers; generate TypeSpec schema witness, compare against the independent JSON Schema in memory, fail closed on drift and attach digest-bound receipts.
- WIT versioned boundaries for accelerator adapters/component interfaces; **binary** tensor data stays out of JSON.
- Pure `.ores` transformer inference/training, batching and actor-based serving; resource quotas and validation at every model import.
- Release gate: reproducible model interchange, training/inference and supervised deployment with compatibility matrix.

## Evidence levels — never conflate these

`UNCONFIGURED` -> `SOURCE_ONLY` -> `REFERENCE_ONLY` -> `EXECUTED_UNATTESTED` -> `VERIFIED_BACKEND`.

- A source-only CI pass verifies repository/workflow syntax but **not** Oreslang execution.
- Python/JS numerical fixtures are independent reference oracles, never a substitute for Oreslang compiler execution.
- A verified backend receipt must bind source Git tree, compiler artifact SHA, backend/target, runtime, actual nonzero test cases, exit status, numerical tolerance and logs.
- LLVM/Java/Wasm/GPU receipts are **separate**; one cannot stand in for another.
- Private Git tree mirroring to a funded external organization requires authorized private publication and exact source tree identity, no copied secrets and no false success on zero job steps.

## Sequencing

P0 remains in draft until a real compiler runs M1/M2/M3 smoke and their ownership semantics are verified.
Create P1 repositories only when the cross-repo numerical ABI and compiler lowering contracts have stable reviewable versions.
Create P2 repositories after P1 passes eager/compiled equivalence and physical device lifecycle gates.

The first release candidate is a **verified CPU tensor-autograd two-layer MLP**, not the entire ecosystem.
