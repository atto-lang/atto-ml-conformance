/** Fail-closed source-text audit of ML host CI. NOT a YAML parser or run attestation. */
export function checkHostOracleWorkflow(text) {
  if (typeof text !== 'string' || text.length > 100_000) throw Error('invalid workflow text');
  const start = text.indexOf('\njobs:\n');
  const nodeStart = text.indexOf('\n  node-reference:\n', start);
  const rustStart = text.indexOf('\n  rust-reference:\n', nodeStart);
  if (start < 0 || nodeStart < 0 || rustStart < 0) throw Error('missing separate jobs');
  const node = text.slice(nodeStart, rustStart);
  const rust = text.slice(rustStart);
  const exactRef = 'ref: ' + '$' + '{{ github.event.pull_request.head.sha || github.sha }}';
  const pinnedCheckout = 'actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683';

  // Refuse duplicate/overridden YAML control keys, including jobs and permission
  // declarations. This is a conservative audit of this fixed workflow profile,
  // not a general YAML parser or trusted execution receipt.
  if (/\r|\t|\0/.test(text)) throw Error('unexpected workflow encoding');
  const active = text.split('\n').filter(line => !/^\s*#/.test(line))
    .map(line => line.replace(/\s+#.*$/, '').replace(/\s+$/, '')).join('\n');
  const top = [...active.matchAll(/^([a-z][a-z0-9-]*):/gm)].map(m => m[1]);
  if (top.join(',') !== 'name,on,permissions,jobs') throw Error('duplicate or unexpected top-level YAML key');
  const permissions = active.match(/^permissions:\n([\s\S]*?)^jobs:$/m)?.[1];
  if (permissions === undefined || permissions.trim() !== 'contents: read') throw Error('permissions drift');
  const jobsOnly = active.slice(active.indexOf('\njobs:\n') + '\njobs:\n'.length);
  const headings = [...jobsOnly.matchAll(/^  ([a-z][a-z0-9-]*):\s*$/gm)].map(m => m[1]);
  if (headings.join(',') !== 'node-reference,rust-reference') throw Error('duplicate, renamed or unexpected job');
  for (const [job, label] of [[node, 'Node'], [rust, 'Rust']]) {

    const activeJob = job.split('\n').filter(line => !/^\s*#/.test(line))
      .map(line => line.replace(/\s+#.*$/, '').replace(/\s+$/, '')).join('\n');
    const fields = [...activeJob.matchAll(/^    ([a-z][a-z0-9-]*):/gm)].map(m => m[1]);
    if (fields.join(',') !== 'runs-on,timeout-minutes,steps') throw Error(label + ' duplicate/unknown job field');
    const timeout = label === 'Node' ? '10' : '15';
    if (!activeJob.includes('    runs-on: ubuntu-24.04\n') ||
        !activeJob.includes('    timeout-minutes: ' + timeout + '\n')) {
      throw Error(label + ' runner or timeout changed');
    }
    const actions = [...activeJob.matchAll(/^      - (.+)$/gm)];
    const expectedActions = label === 'Node'
      ? [
        'uses: ' + pinnedCheckout,
        'name: Verify exact authored source and clean tree',
        'uses: actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020',
        'name: Execute Node reference oracles and provider contract checks',
        'name: Mark executed scope without promoting any guest backend',
      ] : [
        'uses: ' + pinnedCheckout,
        'name: Verify exact authored source and clean tree',
        'name: Require reviewed root Cargo.lock before any Rust test',
        'name: Verify pinned Rust toolchain identity',
        'name: Execute locked Rust receipt-classification tests',
        'name: Mark executed scope without promoting any guest backend',
      ];
    if (actions.map(m => m[1]).join('\n') !== expectedActions.join('\n')) {
      throw Error(label + ' conditional, duplicate or unexpected step');
    }
    for (let i = 0; i < actions.length; i++) {
      const segment = activeJob.slice(actions[i].index, actions[i + 1]?.index ?? activeJob.length);
      const keys = [...segment.matchAll(/^        ([a-z][a-z0-9-]*):/gm)].map(m => m[1]);
      if (new Set(keys).size !== keys.length ||
          keys.some(key => !['with', 'shell', 'env', 'run'].includes(key))) {
        throw Error(label + ' duplicate or unknown step field');
      }
    }
    const number = (pattern) => [...activeJob.matchAll(pattern)].length;
    if (number(/^      - uses: actions\/checkout@/gm) !== 1 ||
        number(/^          ref: .*$/gm) !== 1 ||
        !activeJob.includes('          ' + exactRef + '\n') ||
        number(/^          persist-credentials: .*$/gm) !== 1 ||
        !activeJob.includes('          persist-credentials: false\n') ||
        number(/^          EXPECTED_SOURCE_SHA: .*$/gm) !== 1 ||
        !activeJob.includes('          EXPECTED_SOURCE_SHA: ' + '    if (!job.includes(pinnedCheckout) || !job.includes(exactRef)
        || !job.includes('persist-credentials: false')
        || !job.includes('git rev-parse HEAD')
        || !job.includes('git diff --quiet HEAD --')
        || !job.includes('HOST_REFERENCE_ONLY')) {
      throw Error(label + ' exact-head or nonpromotion boundary missing');
    }
    if (/continue-on-error\s*:\s*true|\|\|\s*true|\|\|\s*:/i.test(job)
        || /^\s+needs\s*:/m.test(job)) {
      throw Error(label + ' job allows bypass or cross-job gating');
    }
  }
  if (!node.includes('run: npm test') || node.includes('cargo test')) {
    throw Error('Node host reference test missing or coupled to Rust');
  }
  if (!rust.includes('if test ! -s Cargo.lock; then')
      || !rust.includes('ROOT_CARGO_LOCK_ABSENT')
      || !rust.includes('cargo test --locked --all-targets')
      || rust.includes('cargo test --all-targets')
      || !rust.includes('rustc --version')
      || !rust.includes('cargo --version')) {
    throw Error('Rust job permits unpinned dependencies or lacks test guard');
  }
  if (!text.includes('permissions:\n  contents: read')) throw Error('workflow permissions widened');
  return 'ML_HOST_WORKFLOW_SOURCE_ONLY_NOT_EXECUTION';
}
 +
                            '{{ github.event.pull_request.head.sha || github.sha }}' + '\n') ||
        !/^          test "\$\(git rev-parse HEAD\)" = "\$EXPECTED_SOURCE_SHA"$/m.test(activeJob) ||
        !/^          git diff --quiet HEAD --$/m.test(activeJob)) {
      throw Error(label + ' exact checkout guard spoofed');
    }
    if (/^\s+(?:if|needs|continue-on-error|environment|permissions|strategy):/m.test(activeJob)) {
      throw Error(label + ' conditional/override field');
    }
    if (!job.includes(pinnedCheckout) || !job.includes(exactRef)
        || !job.includes('persist-credentials: false')
        || !job.includes('git rev-parse HEAD')
        || !job.includes('git diff --quiet HEAD --')
        || !job.includes('HOST_REFERENCE_ONLY')) {
      throw Error(label + ' exact-head or nonpromotion boundary missing');
    }
    if (/continue-on-error\s*:\s*true|\|\|\s*true|\|\|\s*:/i.test(job)
        || /^\s+needs\s*:/m.test(job)) {
      throw Error(label + ' job allows bypass or cross-job gating');
    }
  }
  if (!node.includes('run: npm test') || node.includes('cargo test')) {
    throw Error('Node host reference test missing or coupled to Rust');
  }
  if (!rust.includes('if test ! -s Cargo.lock; then')
      || !rust.includes('ROOT_CARGO_LOCK_ABSENT')
      || !rust.includes('cargo test --locked --all-targets')
      || rust.includes('cargo test --all-targets')
      || !rust.includes('rustc --version')
      || !rust.includes('cargo --version')) {
    throw Error('Rust job permits unpinned dependencies or lacks test guard');
  }
  if (!text.includes('permissions:\n  contents: read')) throw Error('workflow permissions widened');
  return 'ML_HOST_WORKFLOW_SOURCE_ONLY_NOT_EXECUTION';
}
