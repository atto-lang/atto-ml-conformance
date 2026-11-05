// Independent host contract only; not native Oreslang numerical execution.
import test from 'node:test';
import assert from 'node:assert/strict';
import {loadProviderLock,verifyProviderLock,gitBlobSha} from '../src/check-provider-lock.mjs';

const saved=loadProviderLock();
const clone=()=>({lock:structuredClone(saved.lock),documents:structuredClone(saved.documents)});
const rewrite=(bundle,name,change)=>{
  const body=JSON.parse(bundle.documents[name]);change(body);
  const bytes=JSON.stringify(body,null,2)+'\n';
  bundle.documents[name]=bytes;
  bundle.lock.providers.find(x=>x.repository===name).gitBlobSha=gitBlobSha(bytes);
};

test('even matching source contract hashes prove neither guest parity nor export permission', () => {
  const verified=verifyProviderLock(saved.lock,saved.documents);
  assert.equal(verified.guestExecution,false);
  assert.equal(verified.sourceExportAllowed,false);
  assert.equal(verified.releaseReady,false);
});

test('top-level self-certification and private-source export cannot be smuggled', () => {
  const mutations=[
    s=>s.lock.guestEvidence='PASS',
    s=>s.lock.sourceExportsAllowed=true,
    s=>s.lock.requirements.reverse()
  ];
  for(const mutation of mutations){
    const s=clone();mutation(s);
    assert.throws(()=>verifyProviderLock(s.lock,s.documents));
  }
});

test('even updated exact Git blob cannot bless forged compiler proof or invalid source pin', () => {
  const first=clone();
  rewrite(first,'oreslang-ml',d=>{d.hostOracleVerified=true});
  assert.throws(()=>verifyProviderLock(first.lock,first.documents),/contract provenance/);
  const second=clone();
  rewrite(second,'oreslang-tensor',d=>{d.mainSnapshotSha='main'});
  assert.throws(()=>verifyProviderLock(second.lock,second.documents),/contract provenance/);
});
