import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {checkHostOracleWorkflow} from '../src/check-host-oracle-workflow.mjs';
const workflow = readFileSync(new URL('../.github/workflows/oracle-only.yml', import.meta.url), 'utf8');

test('exact ML workflow has independent source-bound Node and locked Rust gates', () => {
  assert.equal(checkHostOracleWorkflow(workflow), 'ML_HOST_WORKFLOW_SOURCE_ONLY_NOT_EXECUTION');
});

test('positive-substring decoys and YAML override mutations cannot certify the workflow', () => {
  const cases = [
    ['cargo test --locked --all-targets', 'cargo test --all-targets'],
    ['if test ! -s Cargo.lock; then', 'if false; then'],
    ['ROOT_CARGO_LOCK_ABSENT', 'IGNORED_LOCKFILE'],
    ['ref: ' + '$' + '{{ github.event.pull_request.head.sha || github.sha }}', 'ref: main'],
    ['persist-credentials: false', 'persist-credentials: true'],
    ['run: npm test', 'run: echo tests-skipped'],
    ['HOST_REFERENCE_ONLY', 'VERIFIED_BACKEND'],
    ['permissions:\n  contents: read', 'permissions:\n  contents: write'],
    ['git diff --quiet HEAD --', 'echo no-diff-check'],
  ];
  for (const [from, to] of cases) {
    assert.ok(workflow.includes(from), 'fixture mismatch: ' + from);
    assert.throws(() => checkHostOracleWorkflow(workflow.replaceAll(from, to)), /REFUSED/, from);
  }
  const mutants = [
    workflow + '\njobs:\n  malicious:\n    runs-on: ubuntu-latest\n',
    workflow.replace('permissions:\n  contents: read', 'permissions:\n  contents: read\npermissions:\n  contents: write'),
    workflow.replace('  rust-reference:', '  node-reference:\n    runs-on: ubuntu-latest\n  rust-reference:'),
    workflow.replace('    steps:\n', '    if: false\n    steps:\n'),
    workflow.replace('    timeout-minutes: 15', '    needs: node-reference\n    timeout-minutes: 15'),
    workflow.replace('    timeout-minutes: 10', '    timeout-minutes: 10\n    steps: []'),
    workflow.replace('      - name: Execute Node reference oracles', '      - if: false\n      - name: Execute Node reference oracles'),
    workflow.replace('      - name: Execute locked Rust', '      - continue-on-error: true\n      - name: Execute locked Rust'),
    workflow.replace('      - name: Execute locked Rust', '      - run: cargo test --locked --all-targets || true\n      - name: Execute locked Rust'),
    workflow.replace('      - name: Execute Node reference oracles', '      - run: npm test || echo skipped\n      - name: Execute Node reference oracles'),
    workflow.replace('      - name: Execute Node reference oracles', '      - run: echo ignored\n      - name: Execute Node reference oracles'),
  ];
  for (let i=0; i<mutants.length; i++) {
    assert.notEqual(mutants[i],workflow);
    assert.throws(() => checkHostOracleWorkflow(mutants[i]), /REFUSED/, 'mutant '+i);
  }
});
