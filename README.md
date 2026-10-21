# Oreslang ML Conformance

Independent numeric fixtures, gradient oracles, runner admission and evidence integrity for the Oreslang-native ML stack.

**Important:** fixture self-tests and host reference-oracle runs are not proof that any Oreslang compiler executed the examples. A real backend is admitted only with verifiable source, build and execution evidence.

See `docs/CONTRACT.md` after bootstrap PR.

## No-Python policy

Python source, scripts, tests, notebooks, package manifests, runtime dependencies, and CI tooling are not permitted in this repository. Host-side conformance/reference tooling must be implemented in Rust with equivalent fail-closed behavior and test coverage. Documentation may mention Python only to describe this policy or historical migration work.
