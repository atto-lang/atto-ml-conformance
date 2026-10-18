# Exact-head host reference evidence

**Status: HOST_REFERENCE_ONLY. Not Oreslang guest, native compiler, or release evidence.**

The independent `.ores` Tensor → Autograd → ML implementation still needs a trusted compiler built from an immutable revision and actual Java/GraalVM and LLVM guest execution. No host-reference green check can replace that.

## Combined source-local gate

The `.github/workflows/host-evidence.yml` workflow:

1. Checks out the **event's exact PR head SHA or pushed SHA** rather than the synthetic pull-request merge ref.
2. Uses SHA-pinned Actions checkout, Node 22, Python 3.12 and artifact uploader, with `contents: read` and checkout credentials not persisted.
3. Runs **all Node host tests** using `npm test`: currently 76 declared cases (36 host numeric, 17 provider ownership/link checks, 12 P0 fixture crosswalk and 11 workspace metadata security tests).
4. Runs all Python unittest files (including the 13-case synthetic receipt admission suite) and `scripts/check_reference.py` against the 10 P0 fixtures.
5. Writes exactly **one metadata JSON file**, `build/host-only-receipt.json`, only if test commands succeed and fail-closed parsers find non-skipped, non-failing, non-duplicated test summaries. `scripts/host_receipt.py` requires the checked-out Git commit to match the event SHA and records its Git tree, test counts, SHA-256 hashes of logs, and an exact reference-check marker.
6. Uploads **only that JSON receipt** under `ml-host-only-exact-head-receipt` with seven-day retention. It does not upload source, private Git trees, test logs, compiler binaries or credentials.

The receipt deliberately declares `source_export_authorized:false`, `private_source_transferred:false`, `native_compiler_executed:false`, `native_guest_executed:false`, and `release_ready:false`. It is a runner-produced **host reference summary**, not a cryptographically signed attestation and not an independent proof of the test binary or runner's trust.

### Evidence already observed

The 17 provider-lock tests passed in isolated JavaScript against exact GitHub module/test blobs, including three mutation cases requiring interface IDs to map to their owning upstream repositories. The receipt implementation and test source match the committed Git blob IDs; its 13 Python tests passed under a local native Python runtime, including a real temporary Git repository whose exact SHA/tree was validated and a wrong-head negative.

Independent, newly authored source-free numeric and synthetic metadata tests ran successfully on private [Scintilla Actions #39098896609](https://github.com/scintilla-run-test/gleam-runner-conformance/actions/runs/39098896609) (50/50). That run neither used nor tested this conformance PR source.

**Source-org CI blocker:** the conformance workflow run [#39138980315](https://github.com/ores-truffle-oreslang/oreslang-ml-conformance/actions/runs/39138980315) at this branch's prior exact head failed **before any executed steps**, with no upload. The full combined Node/Python suite has **not** passed on GitHub Actions. This limitation is independent of synthetic/host carrier capacity.

### Why there is no cross-org private-source mirror

Open [security incident #22](https://github.com/ores-truffle-oreslang/oreslang-platform-conformance/issues/22) and [Scintilla exposure incident #77](https://github.com/ores-truffle-oreslang/oreslang-platform-conformance/issues/77) prohibit treating available alternate-org Actions minutes, private destination visibility, or a copied Git tree as sufficient authorization. Approved export source/destination snapshot and protected-main policy remain absent. Source-free carrier tests may be independently authored there; **do not** move a private repository Git tree or private artifact there without the required independent approvals.

Next: restore source-local Actions runner allocation under [CI recovery #69](https://github.com/ores-truffle-oreslang/oreslang-platform-conformance/issues/69), obtain an exact-head **stepful** host receipt, then run actual pinned Oreslang guest tests with a verified compiler. Keep this PR draft until reviewed and qualified.
