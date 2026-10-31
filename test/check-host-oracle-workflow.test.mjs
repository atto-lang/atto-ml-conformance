import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {checkHostOracleWorkflow} from '../src/check-host-oracle-workflow.mjs';
const workflow = readFileSync(new URL('../.github/workflows/oracle-only.yml', import.meta.url), 'utf8');

test('current ML workflow keeps independent exact-head Node and locked Rust jobs non-promoting', () => {
  assert.equal(checkHostOracleWorkflow(workflow), 'ML_HOST_WORKFLOW_SOURCE_ONLY_NOT_EXECUTION');
});

test('mutants cannot silently disable exact-head, checkout, locking, or test failures', () => {
  const mutants = [
    ['cargo test --locked --all-targets', 'cargo test --all-targets'],
    ['if test ! -s Cargo.lock; then', 'if false; then'],
    ['ROOT_CARGO_LOCK_ABSENT', 'IGNORED_LOCKFILE'],
    ['ref: ' + '$' + '{{ github.event.pull_request.head.sha || github.sha }}', 'ref: main'],
    ['persist-credentials: false', 'persist-credentials: true'],
    ['run: npm test', 'run: echo tests-skipped'],
    ['HOST_REFERENCE_ONLY', 'VERIFIED_BACKEND'],
    ['permissions:\n  contents: read', 'permissions:\n  contents: write'],
    ['git diff --quiet HEAD --', 'echo non-verified-tree'],
  ];
  for (const [from, to] of mutants) {
    assert.ok(workflow.includes(from), 'fixture changed: ' + from);
    assert.throws(() => checkHostOracleWorkflow(workflow.replaceAll(from, to)), undefined, from);
  }
  assert.throws(() => checkHostOracleWorkflow(workflow.replace('    timeout-minutes: 15', '    needs: node-reference\n    timeout-minutes: 15')), /gating/);
  assert.throws(() => checkHostOracleWorkflow(workflow.replace('      - name: Execute locked Rust', '      - run: cargo test --locked --all-targets || true\n      - name: Execute locked Rust')), /bypass/);
});
