# Oreslang ML conformance v1 contract

This is an **independent numeric reference oracle**, not evidence of any Oreslang compiler or runtime execution. The tested reference functions were independently authored in the source-free private funded carrier and copied **inbound** here (never private Oreslang source sent out).

## Cross-repository acceptance

- `oreslang-tensor`: checked element counts, dimension overflow, immutable CPU row-major add and matrix multiply; shape-mismatch and non-finite rejection.
- `oreslang-autograd`: scalar reverse-mode DAG with deterministic shared-subgraph accumulation, immutable saved forward edges, cycle rejection, finite-difference comparison.
- `oreslang-ml`: scalar linear loss and SGD, decreasing-loss oracle without Python/Java/GPU framework implementation.
- `oreslang-common-source`: normative ownership/borrowing and callable/value semantics.
- `oreslang-platform-conformance`: guest execution provenance and exact-head admissibility.

**Fixture IDs:** `tensor/shape/v1`, `tensor/add/v1`, `tensor/matmul/v1`, `autograd/scalar-tape/v1`, `ml/linear-sgd/v1`. A backend must run its own Oreslang sources against these numeric oracles, prove exact compiler/source/test identities, report expected and observed values, and include failing negative tests. Host oracle passes never count as source-language guest execution.

## Verified host-only canary

Source-free funded GitHub Actions [#39093380746](https://github.com/scintilla-run-test/gleam-runner-conformance/actions/runs/39093380746) at head `29cf344b992f1ccae2576aa7bd17fd57a6eb95ea` completed **26/26 tests** on a real Node 22 runner.

- `reference/ml-oracles.mjs` Git blob `c31fec999728a68b8f9d2ee2604bb28f8222e8fa`
- `reference/test/ml-oracles.test.mjs` Git blob `17fbebc27aa9694f051a6a942d307f997303a81c`

These reference fixtures have no Oreslang source, are not a replacement for any backend, and do not grant permission to copy private compiler or actor Git trees. Source exposure incident [platform-conformance #22](https://github.com/ores-truffle-oreslang/oreslang-platform-conformance/issues/22) remains open.
