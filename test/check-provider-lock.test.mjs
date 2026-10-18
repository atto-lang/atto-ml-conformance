import test from "node:test";
import assert from "node:assert/strict";
import {loadProviderLock, verifyProviderLock, gitBlobSha} from "../src/check-provider-lock.mjs";
const initial=loadProviderLock();
function clone(){return {lock:structuredClone(initial.lock),documents:structuredClone(initial.documents)};}
function mutateDoc(s,name,action){
 const data=JSON.parse(s.documents[name]);action(data);
 const next=JSON.stringify(data,null,2)+"\n";s.documents[name]=next;
 s.lock.providers.find(p=>p.repository===name).gitBlobSha=gitBlobSha(next);
}
test("exact three provider Git blobs resolve all required interfaces without guest claims",()=>{
 const r=verifyProviderLock(initial.lock,initial.documents);
 assert.equal(r.providers,3);assert.equal(r.interfaces,3);
 assert.equal(r.guestExecution,false);assert.equal(r.releaseReady,false);
 assert.equal(r.sourceExportAllowed,false);
 assert.equal(r.status,"CONTRACT_LINKS_ONLY_NOT_GUEST_CONFORMANCE");
});
test("mutation of immutable copied Git blob fails",()=>{
 const s=clone();s.documents["oreslang-ml"]+=" ";
 assert.throws(()=>verifyProviderLock(s.lock,s.documents),/provider blob changed/);
});
test("missing provider fails",()=>{
 const s=clone();s.lock.providers.pop();
 assert.throws(()=>verifyProviderLock(s.lock,s.documents),/provider coverage/);
});
test("duplicate provider identity fails",()=>{
 const s=clone();s.lock.providers[1]=structuredClone(s.lock.providers[0]);
 assert.throws(()=>verifyProviderLock(s.lock,s.documents),/unknown or duplicate provider/);
});
test("synthesized success evidence fails, even if hash is updated",()=>{
 const s=clone();mutateDoc(s,"oreslang-autograd",d=>{d.evidence=[{outcome:"success"}]});
 assert.throws(()=>verifyProviderLock(s.lock,s.documents),/contract provenance/);
});
test("guest execution cannot be self-declared",()=>{
 const s=clone();mutateDoc(s,"oreslang-ml",d=>{d.guestExecution="PASS"});
 assert.throws(()=>verifyProviderLock(s.lock,s.documents),/contract provenance/);
});
test("host-oracle pass cannot be misrepresented as integrated",()=>{
 const s=clone();mutateDoc(s,"oreslang-tensor",d=>{d.hostOracleVerified=true});
 assert.throws(()=>verifyProviderLock(s.lock,s.documents),/contract provenance/);
});
test("unknown upstream provider interface fails",()=>{
 const s=clone();mutateDoc(s,"oreslang-ml",d=>{d.requires=["oreslang.gpu.v1"]});
 assert.throws(()=>verifyProviderLock(s.lock,s.documents),/wrong interfaces/);
});
test("autograd tensor edge cannot be dropped",()=>{
 const s=clone();mutateDoc(s,"oreslang-autograd",d=>{d.requires=[]});
 assert.throws(()=>verifyProviderLock(s.lock,s.documents),/wrong interfaces/);
});
test("contract self references are rejected",()=>{
 const s=clone();mutateDoc(s,"oreslang-ml",d=>{d.upstreams.push("oreslang-ml");d.upstreams.sort()});
 assert.throws(()=>verifyProviderLock(s.lock,s.documents),/wrong interfaces/);
});
test("reordered/repeated requirements rejected",()=>{
 const s=clone();s.lock.requirements.push(s.lock.requirements[0]);
 assert.throws(()=>verifyProviderLock(s.lock,s.documents),/sorted and distinct/);
});
test("provider path traversals are rejected before file loading",()=>{
 const s=clone();s.lock.providers[0].path="../private";
 assert.throws(()=>verifyProviderLock(s.lock,s.documents),/unsafe path/);
});
test("cross-organization release promotion blocked",()=>{
 const s=clone();s.lock.sourceExportsAllowed=true;
 assert.throws(()=>verifyProviderLock(s.lock,s.documents),/promotion or cross-org-export/);
});
test("noncanonical JSON is refused even with an updated SHA",()=>{
 const s=clone();s.documents["oreslang-tensor"]=s.documents["oreslang-tensor"].trim();
 s.lock.providers.find(p=>p.repository==="oreslang-tensor").gitBlobSha=gitBlobSha(s.documents["oreslang-tensor"]);
 assert.throws(()=>verifyProviderLock(s.lock,s.documents),/noncanonical/);
});

test("autograd interface cannot omit its tensor-owning upstream despite a re-pinned blob",()=>{
 const s=clone();mutateDoc(s,"oreslang-autograd",d=>{
   d.upstreams=d.upstreams.filter(name=>name!=="oreslang-tensor");
 });
 assert.throws(()=>verifyProviderLock(s.lock,s.documents),/missing upstream owner/);
});
test("ML consumer cannot omit its autograd-owning upstream despite a re-pinned blob",()=>{
 const s=clone();mutateDoc(s,"oreslang-ml",d=>{
   d.upstreams=d.upstreams.filter(name=>name!=="oreslang-autograd");
 });
 assert.throws(()=>verifyProviderLock(s.lock,s.documents),/missing upstream owner/);
});
test("ML consumer cannot omit its tensor-owning upstream despite a re-pinned blob",()=>{
 const s=clone();mutateDoc(s,"oreslang-ml",d=>{
   d.upstreams=d.upstreams.filter(name=>name!=="oreslang-tensor");
 });
 assert.throws(()=>verifyProviderLock(s.lock,s.documents),/missing upstream owner/);
});
