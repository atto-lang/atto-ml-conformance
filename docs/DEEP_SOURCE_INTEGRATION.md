# Cross-repository Oreslang source-import admission (P0)

**Status: STATIC_IMPORT_CLOSURE_NOT_COMPILED.** This review branch does not certify Java/GraalVM or LLVM guest execution, actor ownership or release readiness.

## Pinned source boundary

The independently reviewed metadata-only \`integration/ml-source-blob-lock.v1.json\` pins **14 private Oreslang source-unit Git blob SHA-1 identifiers**, without copying the source bytes to a carrier:

| Provider | Pinned .ores units | Direct cross-repository source imports |
| --- | ---: | --- |
| \`oreslang-tensor\` | 4 | No cross-provider imports |
| \`oreslang-autograd\` | 6 | Imports public Tensor classes/functions from \`oreslang-tensor\` |
| \`oreslang-ml\` | 4 | Imports public Tape/forward/backward from \`oreslang-autograd\` |

There are **52 declared imported symbols** in the current checked-in 14-unit source snapshot. Direct source edges are exactly **Autograd → Tensor** and **ML → Autograd**; ML reaches Tensor transitively. The separate proposed v1 registry also includes **ML → Tensor** as a desired interface dependency; do not claim it is a compiled direct source import yet.

Before \`scripts/run_workspace.py\` starts its first guest job it already rejects missing/incorrect Git commit pins, unexpected Git trees and dirty checkouts. It now also invokes \`scripts/check_workspace_imports.py\` using the locked snapshot. That preflight rejects malformed imports, unknown external packages, missing or non-public symbols, path traversal, symlinks, cycles, source file-count drift, new or changed source Git blobs, ambiguous JSON, unsupported dependency edges, and false guest/export status.

Local verification from a **trusted** and explicitly authorized same-organization sibling checkout:

\`\`\`sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/check_workspace_imports.py \
  --workspace /trusted/oreslang-three-repo-workspace \
  --source-lock integration/ml-source-blob-lock.v1.json
\`\`\`

The second command prints an import-closure summary without invoking a compiler. The full opt-in \`run_workspace.py\` still requires an independent, genuine compiler executable and verifies all three source commit/tree pairs before executing any smoke script. Its \`EXECUTED_UNATTESTED\` markers can be forged by an untrusted executable; real release proof requires independently verified source-to-binary compiler provenance and guest-level negative semantics.

**Security constraints:** never export this private Git tree to a differently funded organization merely because another GitHub Actions runner has minutes. Security incidents [#22](https://github.com/ores-truffle-oreslang/oreslang-platform-conformance/issues/22) and [#77](https://github.com/ores-truffle-oreslang/oreslang-platform-conformance/issues/77) remain open, so source-bearing alternate-org mirroring is prohibited. The source lock itself contains only paths and existing Git identifiers. Separately authored source-free reference oracles remain HOST_ONLY evidence.

The exact same metadata Git blob is imported into the central [56-repo integration draft](https://github.com/ores-truffle-oreslang/oreslang-platform-conformance/pull/79), which structurally rejects changed upstream ownership without claiming any actual compiler result.

Next implementation acceptance: confirm exact SHA-pinned compiler support for the imported \`.ores\` syntax, storage alias/unique-loan enforcement, deterministic VJP values/shape failure paths and two-layer training loss on both GraalVM and LLVM.
