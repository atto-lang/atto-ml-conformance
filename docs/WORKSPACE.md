# Multi-repository, pinned end-to-end P0 smoke

Check out the three producer repositories as siblings under a trusted directory:

```text
workspace/
  oreslang-tensor/
  oreslang-autograd/
  oreslang-ml/
```

Check out exactly the three commits in `manifests/p0-workspace.json`,
not floating branch heads; keep working trees clean. Build and independently
verify a real Oreslang compiler from its own pinned source tree. The
operator must supply that executable explicitly.

From this conformance repository run:

```sh
python3 scripts/check_reference.py fixtures/p0-v1.json
python3 scripts/run_workspace.py \
  --workspace /absolute/path/to/workspace \
  --compiler /absolute/path/to/trusted/oreslang
```

The first command performs **REFERENCE_ONLY** numerical checks. The
second command actually calls four `.ores` smoke programs (including an
autograd-trained affine model), requires matching pinned clean checkout
commits, exact success markers, and captures bounded digest receipts.

The second command refuses to run if a compiler is missing. It does **not**
cryptographically attest that the supplied executable was built from claimed
compiler source. Never promote its result to a backend-parity/release claim
without independently verified build logs, full source/toolchain provenance,
and source/tree identity checks. Executing supplied code is not sandboxed;
only use trusted compiler/checkouts in a restricted development runner.

The sibling source files' original repository PRs are draft and may advance;
regenerate the manifest explicitly when reviewing new exact commits.
