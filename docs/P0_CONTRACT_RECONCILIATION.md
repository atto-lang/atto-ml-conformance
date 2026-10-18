# P0 implementation and proposed integration reconciliation

This review branch is based on **P0 implementation PR #1** at `0f20ce256cb462bb18546f5285c752c2cd184e65` and combines the **proposed contract / independent host oracle PR #3** at `e39fb0c5be53c23eb271c58c62471f34dfb9240d`. No Oreslang source files were copied outside the source organization.

## Two distinct independent numeric references

- The existing `fixtures/p0-v1.json` and `scripts/check_reference.py` are Python-only P0 numeric oracles with six cases. They **never execute the Oreslang guest**.
- `reference/ml-oracles.mjs` and `reference/test/ml-oracles.test.mjs` are independently authored JavaScript host-only references. The exact pair previously passed **26/26** on the funded private source-free carrier [run #39093380746](https://github.com/scintilla-run-test/gleam-runner-conformance/actions/runs/39093380746).
- `integration/p0-fixture-crosswalk.v1.json` maps the four overlapping P0 fixture IDs to their proposed v1 contract IDs, records one missing explicit P0 shape fixture, and discloses P0-only ReLU and sum cases. `test/p0-fixture-crosswalk.test.mjs` runs nine checks against actual P0 data and imported JS oracles.
- `contracts/provider-lock.v1.json` pins three same-organization provider contract Git blob hashes. These contracts remain proposed interfaces, **not compiled integration proof**.
- `manifests/p0-workspace.json` now pins the three *reconciled* P0 source+contract branch commits, rather than the earlier stale implementation heads. `scripts/run_workspace.py` still rejects unpinned or dirty sibling checkouts and requires an operator-supplied real executable Oreslang compiler.

## How to check

```sh
npm test
python3 -m unittest discover -s tests -p "test_*.py"
python3 scripts/check_reference.py fixtures/p0-v1.json
# Only with trusted source checkouts, verified compiler provenance and authorized source-org runner:
python3 scripts/run_workspace.py --workspace /trusted/pinned/workspace --compiler /trusted/pinned/oreslang
```

Node and Python host checks do not authenticate a compiler. The local guest runner's success markers can be forged by an untrusted executable; independent build/source/runner provenance and negative semantic tests are necessary before an `EXECUTED_UNATTESTED` result may be promoted. No CI source export to other orgs is authorized while [security incident #22](https://github.com/ores-truffle-oreslang/oreslang-platform-conformance/issues/22) and protected-main approval requirements remain unresolved.

All new code remains on draft branches. The original P0 implementation, current JavaScript reference and Python reference are deliberately preserved as independently reviewable components.
