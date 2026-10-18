# ML P0 conformance and truthful evidence contract

## Two completely separate gates

1. **REFERENCE_ONLY:** the Python standard-library oracle validates JSON fixture
   integrity and independently recomputes small mathematical results. This is
   *not* Oreslang execution or backend parity.
2. **EXECUTED_UNATTESTED:** compile/execute the actual `.ores` smoke programs
   from `oreslang-tensor`, `oreslang-autograd`, and `oreslang-ml`
   with exact pinned compiler artifacts and record the executable digest,
   source Git tree/commit, stdout/stderr, exit code and running environment.
   Independent source/build provenance is required before declaring support.
3. **VERIFIED_BACKEND:** after independent source/compiler binary provenance,
   stepful target-specific guest execution, and complete evidence receipts; do
   not infer LLVM AOT, Wasm, or GPU parity from Java or reference results.

Never label a fixture self-test, fake runner, static grep, parser rejection, or
zero-step GitHub Actions run as real language execution.

## Fixture contract

- Version: `oreslang-ml-fixtures/v1`.
- Data-only JSON, strictly bounded to 128 KiB and 100 cases.
- Stable IDs, no duplicate JSON keys, boolean-as-number or nonfinite input.
- f64 CPU reference tolerances: atol + rtol * abs(expected).
- Ten independent initial cases: dense operators, scalar DAG/ReLU VJPs and
  a two-layer scalar-autograd training convergence fixture.
- Strict shape/rank, tape topological-edge and training input checks.
- No operation implies accelerator availability or a benchmark speedup.

## Next steps

- Add a real compiler execution adapter, bound output capture and pinned SHA
  receipts. Keep UNCONFIGURED and NO_STEPS different from PASS.
- Execute positive and negative `.ores` cases with exact-tree private CI,
  keeping private compiler blobs in authorized private carriers only.
- Extend fixtures to zero extents, broadcast and reverse sum-to-shape,
  strides, NaNs and overlap/cancellation after semantic contracts are frozen.
- Add directional-derivative and numerical finite-difference tests for every
  autograd VJP, not just scalar add/mul.
- Connect the general `oreslang-platform-conformance` ingestion pipeline.
