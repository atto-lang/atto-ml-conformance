import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {auditWorkspaceMetadata,githubMetadataReader} from "../src/workspace-metadata-audit.mjs";
const source=JSON.parse(readFileSync(new URL("../manifests/p0-workspace.json",import.meta.url),"utf8"));
const ids={"oreslang-tensor":1423912926,"oreslang-autograd":1423913203,"oreslang-ml":1423913534};
function fake(options={}) {
 const calls=[];
 async function readJson(path){
  calls.push(path);
  const match=/^\/repos\/ores-truffle-oreslang\/(oreslang-(?:tensor|autograd|ml))(?:\/git\/commits\/([a-f0-9]{40}))?$/.exec(path);
  assert.ok(match,"no nonallowlisted GitHub endpoint");
  const [,name,commit]=match;
  if(!commit)return {id:options.idString?String(ids[name]):options.wrongId?2:ids[name],
    full_name:"ores-truffle-oreslang/"+name,private:options.public?false:true,
    archived:options.archived?true:false,default_branch:"main"};
  return {sha:options.wrongCommit?"f".repeat(40):source.repositories[name],
    tree:{sha:options.wrongTree?"b".repeat(40):source.source_trees[name]}};
 }
 return {calls,readJson};
}
test("all three pinned exact Git commits and trees are verified without guest claims",async()=>{
 const f=fake(),r=await auditWorkspaceMetadata(source,f.readJson);
 assert.equal(r.repositoriesChecked,3);assert.equal(f.calls.length,6);
 assert.equal(r.status,"METADATA_COMMIT_TREE_MATCH_NOT_GUEST_PROOF");
 assert.equal(r.sourceFilesFetched,0);assert.equal(r.sourceExportAuthorized,false);
 assert.equal(r.guestExecution,false);assert.equal(r.releaseReady,false);
});
test("reject replaced repository identity",async()=>{
 await assert.rejects(()=>auditWorkspaceMetadata(source,fake({wrongId:true}).readJson),/repository identity/);
});
test("reject IDs with ambiguous JSON type",async()=>{
 await assert.rejects(()=>auditWorkspaceMetadata(source,fake({idString:true}).readJson),/repository identity/);
});
test("reject public/archived repository changes",async()=>{
 for(const option of [{public:true},{archived:true}])
  await assert.rejects(()=>auditWorkspaceMetadata(source,fake(option).readJson),/repository identity/);
});
test("reject missing pinned commit even when tree matches",async()=>{
 await assert.rejects(()=>auditWorkspaceMetadata(source,fake({wrongCommit:true}).readJson),/missing commit/);
});
test("reject changed Git source tree under pinned SHA",async()=>{
 await assert.rejects(()=>auditWorkspaceMetadata(source,fake({wrongTree:true}).readJson),/tree mismatch/);
});
test("do not request private metadata with unpinned commits",async()=>{
 const m=structuredClone(source);m.repositories["oreslang-ml"]="branch-name";
 const f=fake();
 await assert.rejects(()=>auditWorkspaceMetadata(m,f.readJson),/immutable commit/);
 assert.equal(f.calls.length,0);
});
test("deny missing source tree or additional unreviewed repository",async()=>{
 for(const edit of [m=>delete m.source_trees["oreslang-tensor"],m=>m.repositories["attack-repo"]="a".repeat(40)])
  await assert.rejects(()=>auditWorkspaceMetadata((()=>{const x=structuredClone(source);edit(x);return x})(),fake().readJson),/provider identity set/);
});
test("deny promotion of unexecuted source or fake compiler attestation",async()=>{
 for(const edit of [m=>m.compiler_artifact="verified",m=>m.source_state="GUEST_PASSED"])
  await assert.rejects(()=>auditWorkspaceMetadata((()=>{const x=structuredClone(source);edit(x);return x})(),fake().readJson),/admission/);
});
test("read-only metadata requester disallows foreign organizations and source access",async()=>{
 const calls=[];
 const get=githubMetadataReader("synthetic-readonly-token",async(url,opts)=>{
    calls.push({url,opts});return {ok:true,status:200,text:async()=>JSON.stringify({id:123})};
 });
 await get("/repos/ores-truffle-oreslang/oreslang-tensor");
 await get("/repos/ores-truffle-oreslang/oreslang-ml/git/commits/"+"a".repeat(40));
 assert.equal(calls.length,2);
 assert.ok(calls.every(x=>x.opts.method==="GET"&&x.opts.redirect==="error"&&x.url.startsWith("https://api.github.com/")));
 for(const bad of ["/repos/other-org/oreslang-ml",
 "/repos/ores-truffle-oreslang/oreslang-ml/contents/src/main.ores",
 "/repos/ores-truffle-oreslang/oreslang-ml/git/trees/"+"a".repeat(40),
 "/repos/ores-truffle-oreslang/oreslang-ml/../oreslang-tensor",
 "/repos/ores-truffle-oreslang/oreslang-ml?query=1"])
   await assert.rejects(()=>get(bad),/API path/);
 assert.equal(calls.length,2);
});
test("reject unsafe token or denied API responses",async()=>{
 assert.throws(()=>githubMetadataReader("bad\nsecret"),/read-only token/);
 assert.throws(()=>githubMetadataReader(""),/read-only token/);
 const get=githubMetadataReader("synthetic-readonly-token",async()=>({ok:false,status:403}));
 await assert.rejects(()=>get("/repos/ores-truffle-oreslang/oreslang-ml"),/HTTP 403/);
});
