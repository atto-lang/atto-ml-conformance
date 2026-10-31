import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const y = readFileSync(new URL('../.github/workflows/root-cargo-lock-proposal.yml', import.meta.url), 'utf8');

// Static review aid only: not YAML semantics or authenticated CI evidence.
function inspect(s) {
  for (const required of [
    'permissions:\n  contents: read',
    'persist-credentials: false',
    'cargo +1.95.0 generate-lockfile',
    'cargo +1.95.0 test --locked --all-targets',
    'test ! -e Cargo.lock',
    'SOURCE_LOCAL_LOCK_PROPOSAL_UNATTESTED',
    '"guestExecuted":false,"releaseReady":false',
    'retention-days: 1',
    'ml-root-lock-proposal/Cargo.lock.sha256',
    'ml-root-lock-proposal/receipt.json',
  ]) assert.ok(s.includes(required), required);
  assert.equal((s.match(/^jobs:$/gm) || []).length,1);
  assert.equal((s.match(/^permissions:$/gm) || []).length,1);
  assert.equal((s.match(/^  propose-root-lock:$/gm) || []).length,1);
  assert.equal((s.match(/^        uses: actions\/upload-artifact@/gm) || []).length,1);
  assert.equal((s.match(/^        uses: actions\/checkout@/gm) || []).length,1);
  assert.ok(!/git push|repository_dispatch|workflow_run|create-pull-request/.test(s));
  const tail=s.split('      - name: Upload only proposed lockfile and source-local review receipt')[1];
  assert.ok(tail);
  const paths=[...tail.matchAll(/^            (\$\{\{ runner\.temp \}\}\/.*)$/gm)].map(x=>x[1]);
  assert.deepEqual(paths,[
    '${{ runner.temp }}/ml-root-lock-proposal/Cargo.lock',
    '${{ runner.temp }}/ml-root-lock-proposal/Cargo.lock.sha256',
    '${{ runner.temp }}/ml-root-lock-proposal/receipt.json',
  ]);
}
test('only a read-only source-local Cargo lock proposal is allowed',()=>inspect(y));
test('authorization and execution claim mutants are rejected',()=>{
  for (const [from,to] of [
    ['permissions:\n  contents: read','permissions:\n  contents: write'],
    ['persist-credentials: false','persist-credentials: true'],
    ['cargo +1.95.0 generate-lockfile','echo fake'],
    ['cargo +1.95.0 test --locked --all-targets','cargo test --all-targets'],
    ['test ! -e Cargo.lock','echo ignore existing lock'],
    ['"guestExecuted":false,"releaseReady":false','"guestExecuted":true,"releaseReady":true'],
    ['retention-days: 1','retention-days: 90'],
    ['${{ runner.temp }}/ml-root-lock-proposal/receipt.json','${{ runner.temp }}/private-source.zip'],
  ]) {
    assert.ok(y.includes(from),from);
    assert.throws(()=>inspect(y.replaceAll(from,to)),undefined,from);
  }
  assert.throws(()=>inspect(y+'\njobs:\n  unsafe:\n    runs-on: ubuntu-latest\n'));
});
