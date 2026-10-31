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
  for (const [job, label] of [[node, 'Node'], [rust, 'Rust']]) {
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
