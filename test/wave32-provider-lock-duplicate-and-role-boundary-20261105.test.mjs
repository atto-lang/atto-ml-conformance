// Host-only provider lock contract; not numeric guest execution or parity.
import test from 'node:test';
import assert from 'node:assert/strict';
import {loadProviderLock,verifyProviderLock,gitBlobSha}
  from '../src/check-provider-lock.mjs';

const initial=loadProviderLock();
const clone=()=>({lock:structuredClone(initial.lock),documents:structuredClone(initial.documents)});
function modify(s,repo,mutation){
  const doc=JSON.parse(s.documents[repo]);
  mutation(doc);
  const bytes=JSON.stringify(doc,null,2)+'\n';
  s.documents[repo]=bytes;
  s.lock.providers.find(x=>x.repository===repo).gitBlobSha=gitBlobSha(bytes);
}
test('provider lock remains source-only and never a guest success receipt',()=>{
  const result=verifyProviderLock(initial.lock,initial.documents);
  assert.equal(result.hostReferenceRunsNotEvidence,true);
  assert.equal(result.guestExecution,false);
  assert.equal(result.releaseReady,false);
});
test('updated correct Git blob cannot make duplicate fixture IDs admissible',()=>{
  const x=clone();
  modify(x,'oreslang-tensor',d=>{d.fixtureIds=['duplicate','duplicate']});
  assert.throws(()=>verifyProviderLock(x.lock,x.documents),/sorted and distinct/);
});
test('updated correct Git blob cannot introduce unauthorized provider fields',()=>{
  const x=clone();
  modify(x,'oreslang-autograd',d=>{d.compilerVerified=true});
  assert.throws(()=>verifyProviderLock(x.lock,x.documents),/contract fields/);
});
