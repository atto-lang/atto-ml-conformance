# Oreslang ML Conformance

Independent numeric fixtures, gradient oracles, runner admission and evidence integrity for the Oreslang-native ML stack.

**Important:** fixture self-tests and Rust host-oracle runs are not proof that any Oreslang compiler executed the examples. A real backend is admitted only with verifiable source, build and execution evidence.

See `docs/CONTRACT.md` after bootstrap PR.

## Repository ownership and migration (2026-11-08)

**Current:** `ores-truffle-oreslang/oreslang-ml-conformance` in the old Oreslang org. **Public language:** AttoLang. Retain existing `.ores` files and historical repository/package/CLI aliases until compiler-backed `.atto` support and consumers have been validated.

- **This repo owns:** ML portability fixtures, numerical tolerance policies and pinned executable compiler receipts.
- **Not owned here:** claiming guest parity from source-only or zero-step CI.
- **Organizations:** [atto-lang](https://github.com/atto-lang) is for language/compiler/tooling, portable ML/scientific libraries, conformance and demonstrations. [atto-co](https://github.com/atto-co) is for independently governed cloud hosting, deployment, tenant identity, billing and commercial services. Similar `atto-*` repo names do not imply transferred source ID or content parity.
- **Migration proposal:** identity-preserving GitHub transfer under the original repository name to `atto-lang/oreslang-ml-conformance` after reviews. No legacy-org direct move to `atto-co` is currently authorized. Later commercialization spinouts need their own signed off runbook.

**Repository transfer gates:** coordinate a single owner/rollback plan at [issue #26](https://github.com/ores-truffle-oreslang/.github/issues/26); consult private [runbook #25](https://github.com/ores-truffle-oreslang/.github/pull/25). Record exact source commit SHA/tree and numeric ID, target visibility and protection/rulesets, source/target admin and independent security approvals, PRs/tags/releases, packages/import consumers, webhooks, GitHub Apps, Actions/billing/runners, secrets and Pages. Never mirror private source without separate approval. After actual GitHub transfer verify identical ID/history/tree, restore protections, update references independently and run exact-head CI with nonzero executed steps. `steps=[]`/`null` is `NOT_EXECUTED`; host/static tests cannot establish compiled AttoLang numerical or guest execution parity.
