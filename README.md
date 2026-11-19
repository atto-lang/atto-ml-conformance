> **AI agent instructions (organization-wide):** Before working on code, issues, or pull requests, read and follow the [organization `AGENTS.md`](https://github.com/ores-truffle-oreslang/.github/blob/main/AGENTS.md), including its **merge-first stealth-development policy**. Honor any repository-local `AGENTS.md`, explicit holds, and GitHub-enforced rules.

# Oreslang ML Conformance

## AttoLang naming migration and language authority (2026-11-18)

The public language name is **AttoLang** (formerly **Oreslang**). This is a historical `ores-truffle-oreslang/oreslang-ml-conformance` checkout; its current ecosystem routing is **[atto-lang/atto-ml-conformance](https://github.com/atto-lang/atto-ml-conformance)**. ML conformance requires target-specific executable tests and explicit unsupported results. A similarly named repository is not evidence of identical commits, GitHub issue/PR history or feature status.

**[atto-lang/atto-spec](https://github.com/atto-lang/atto-spec) is the canonical normative language specification.** Use [atto-platform-conformance](https://github.com/atto-lang/atto-platform-conformance) for executable positive/negative guest fixtures, [atto-compilers-parity-testing](https://github.com/atto-lang/atto-compilers-parity-testing) for cross-backend comparisons, and [atto-common-source](https://github.com/atto-lang/atto-common-source) for portable `.atto` core/std code. Modern proposed language rules include `snake_case` callable naming, `borrow!`/`take!`/`share!`/`copy!`/`copy!!`, [default nonprimitive argument borrowing](https://github.com/atto-lang/atto-spec/blob/main/language/implicit-argument-borrow-v1.md), [static `define const` including one-time `os.read_env`](https://github.com/atto-lang/atto-spec/blob/main/language/file-module-const-v1.md), and [`<<<`/`>>>`/`ashr` shifts versus `<<`/`>>` stream I/O](https://github.com/atto-lang/atto-spec/blob/main/language/bitwise-and-stream-operators-v1.md). Contract status and compiler execution evidence take precedence over old README descriptions.

Retain actual legacy `.ores` files, CLI/package/ABI names and reproducible commands below until each replacement is separately implemented and verified. No Python scripts, CI/test support or generators for new AttoLang work; favor Rust support tooling. No feature or parity claim without exact SHA/tree, toolchain/target, real compiled guest execution and negative tests; host-only tests or zero executed CI steps count as **not executed**.

Independent numeric fixtures, gradient oracles, runner admission and evidence integrity for the Oreslang-native ML stack.

**Important:** fixture self-tests and Rust host-oracle runs are not proof that any Oreslang compiler executed the examples. A real backend is admitted only with verifiable source, build and execution evidence.

See `docs/CONTRACT.md` after bootstrap PR.
