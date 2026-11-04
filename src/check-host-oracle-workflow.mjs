/**
 * Conservative source-only audit for the fixed ML CI profile, not a generic
 * YAML parser or an authenticated GitHub Actions execution receipt.
 * Fail closed on any unknown YAML control surface rather than trusting
 * positive substrings that an attacker could place in comments/duplicate keys.
 */
export function checkHostOracleWorkflow(source) {
  function refuse(reason) { throw Error('ML_HOST_WORKFLOW_REFUSED: ' + reason); }
  if (typeof source !== 'string' || source.length === 0 || source.length > 100_000 || /\r|\t|\0/.test(source)) {
    refuse('invalid workflow text');
  }
  const lines = source.split('\n')
    .filter(line => !/^\s*#/.test(line))
    .map(line => line.replace(/\s+#.*$/, '').replace(/\s+$/, ''));
  const text = lines.join('\n');
  const occurrences = (pattern, data = text) => [...data.matchAll(pattern)].length;
  const top = lines.filter(line => /^[a-z][a-z0-9-]*:/.test(line)).map(line => line.match(/^([a-z][a-z0-9-]*):/)[1]);
  if (top.join(',') !== 'name,on,permissions,jobs') refuse('unexpected or duplicate top-level key');
  const perms = text.match(/^permissions:\n([\s\S]*?)^jobs:$/m)?.[1];
  if (perms === undefined || perms.trim() !== 'contents: read') refuse('permissions not exactly read-only');
  const body = text.slice(text.indexOf('\njobs:\n') + '\njobs:\n'.length);
  const headers = [...body.matchAll(/^  ([a-z][a-z0-9-]*):\s*$/gm)];
  if (headers.length !== 2 || headers[0][1] !== 'node-reference' || headers[1][1] !== 'rust-reference') {
    refuse('missing, duplicate or unexpected job');
  }
  const node = body.slice(headers[0].index, headers[1].index);
  const rust = body.slice(headers[1].index);
  const expectedRef = 'ref: ' + '$' + '{{ github.event.pull_request.head.sha || github.sha }}';
  const expectedSha = 'EXPECTED_SOURCE_SHA: ' + '$' + '{{ github.event.pull_request.head.sha || github.sha }}';
  const checkout = 'actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683';
  for (const [job, name, timeout] of [[node, 'Node', '10'], [rust, 'Rust', '15']]) {
    const fields = [...job.matchAll(/^    ([a-z][a-z0-9-]*):/gm)].map(m => m[1]);
    if (fields.join(',') !== 'runs-on,timeout-minutes,steps') refuse(name + ' illegal or duplicate job field');
    const actions = [...job.matchAll(/^      - (.+)$/gm)];
    const expected = name === 'Node'
      ? [
        'uses: ' + checkout,
        'name: Verify exact authored source and clean tree',
        'uses: actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020',
        'name: Execute Node reference oracles and provider contract checks',
        'name: Mark executed scope without promoting any guest backend',
      ] : [
        'uses: ' + checkout,
        'name: Verify exact authored source and clean tree',
        'name: Require reviewed root Cargo.lock before any Rust test',
        'name: Verify pinned Rust toolchain identity',
        'name: Execute locked Rust receipt-classification tests',
        'name: Mark executed scope without promoting any guest backend',
      ];
    if (actions.map(m => m[1]).join('\n') !== expected.join('\n')) {
      refuse(name + ' unexpected, conditional or duplicate workflow step');
    }
    for (let i = 0; i < actions.length; i++) {
      const segment = job.slice(actions[i].index, actions[i+1]?.index ?? job.length);
      const keys = [...segment.matchAll(/^        ([a-z][a-z0-9-]*):/gm)].map(m => m[1]);
      if (new Set(keys).size !== keys.length
          || keys.some(key => !['with', 'shell', 'env', 'run'].includes(key))) {
        refuse(name + ' repeated or unexpected step key');
      }
    }
    if (!job.includes('    runs-on: ubuntu-24.04\n') || !job.includes('    timeout-minutes: ' + timeout + '\n')) refuse(name + ' runner/timeout drift');
    if (occurrences(new RegExp('^      - uses: ' + checkout + '$', 'gm'), job) !== 1
      || occurrences(/^          ref: .*$/gm, job) !== 1
      || !job.includes('          ' + expectedRef + '\n')
      || occurrences(/^          persist-credentials: .*$/gm, job) !== 1
      || !job.includes('          persist-credentials: false\n')
      || occurrences(/^          EXPECTED_SOURCE_SHA: .*$/gm, job) !== 1
      || !job.includes('          ' + expectedSha + '\n')
      || !/^          test "\$\(git rev-parse HEAD\)" = "\$EXPECTED_SOURCE_SHA"$/m.test(job)
      || !/^          git diff --quiet HEAD --$/m.test(job)
      || !/^          test -z "\$\(git ls-files --others --exclude-standard\)"$/m.test(job)
      || !job.includes('HOST_REFERENCE_ONLY')) refuse(name + ' exact-head and scope guard');
    if (/^\s+(?:if|needs|continue-on-error|environment|permissions|strategy|container|services|uses):/m.test(job)
      || /\|\|\s*(?:true|:|echo|exit\s+0)/.test(job)
      || /\bset\s+\+e\b/.test(job)) refuse(name + ' conditional/bypass control');
  }
  if (occurrences(/^        run: npm test$/gm, node) !== 1 || /cargo test/.test(node)) refuse('Node oracle incorrectly coupled');
  if (!/^          if test ! -s Cargo\.lock; then$/m.test(rust)
    || !/^            exit 1$/m.test(rust)
    || !rust.includes('ROOT_CARGO_LOCK_ABSENT')
    || occurrences(/^          cargo test --locked --all-targets$/gm, rust) !== 1
    || /cargo test --all-targets/.test(rust)
    || !/^          test "\$\(rustc --version \| awk '\{print \$2\}'\)" = "1\.95\.0"$/m.test(rust)
    || !/^          test "\$\(cargo --version \| awk '\{print \$2\}'\)" = "1\.95\.0"$/m.test(rust)) {
    refuse('Rust lock/toolchain gate not enforced');
  }
  return 'ML_HOST_WORKFLOW_SOURCE_ONLY_NOT_EXECUTION';
}
