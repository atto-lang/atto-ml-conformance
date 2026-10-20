import {readFileSync} from "node:fs";
import {createHash} from "node:crypto";
const roles = new Map([
  ["oreslang-tensor", "oreslang.tensor.cpu.v1"],
  ["oreslang-autograd", "oreslang.autograd.scalar.v1"],
  ["oreslang-ml", "oreslang.ml.linear-sgd.v1"]
]);
const needs = new Map([
  ["oreslang-tensor", []],
  ["oreslang-autograd", ["oreslang.tensor.cpu.v1"]],
  ["oreslang-ml", ["oreslang.autograd.scalar.v1", "oreslang.tensor.cpu.v1"]]
]);
const fields = ["schemaVersion","organization","repository","mainSnapshotSha","kind",
  "provides","requires","upstreams","fixtureIds","hostOracleRepo","hostOracleVerified",
  "guestExecution","evidence","nextGate"];
function fail(msg){throw Error("ML_CONTRACT_REJECTED: " + msg);}
function plain(x,expected,which){
 if(!x || Array.isArray(x) || typeof x!=="object" ||
    JSON.stringify(Object.keys(x).sort())!==JSON.stringify([...expected].sort()))
  fail(which+" fields");
}
function distinctSorted(xs,which) {
 if(!Array.isArray(xs) || xs.some(x=>typeof x!=="string" || x.length===0))
  fail(which+" invalid list");
 if(xs.some((x,i)=>i>0 && xs[i-1]>=x))fail(which+" must be sorted and distinct");
}
export function gitBlobSha(s) {
 const b=Buffer.from(s,"utf8");
 return createHash("sha1").update("blob "+b.length+"\0").update(b).digest("hex");
}
export function verifyProviderLock(lock,documents){
 plain(lock,["schemaVersion","organization","kind","providers","requirements",
    "guestEvidence","sourceExportsAllowed"],"lock");
 if(lock.schemaVersion!==1 || lock.organization!=="ores-truffle-oreslang" ||
    lock.kind!=="PROPOSED_PROVIDER_METADATA_NOT_GUEST_EXECUTION" ||
    lock.guestEvidence!=="NOT_EXECUTED" || lock.sourceExportsAllowed!==false)
  fail("promotion or cross-org-export claim");
 if(!Array.isArray(lock.providers) || lock.providers.length!==3 ||
    !documents || typeof documents!=="object")fail("provider coverage");
 distinctSorted(lock.requirements,"required interfaces");
 const seen=new Set(),satisfied=new Set();
 for(const entry of lock.providers) {
   plain(entry,["repository","path","gitBlobSha"],"provider pin");
   if(!roles.has(entry.repository) || seen.has(entry.repository))
     fail("unknown or duplicate provider");
   seen.add(entry.repository);
   if(entry.path!=="contracts/providers/"+entry.repository+".v1.json" ||
      !/^[a-f0-9]{40}$/.test(entry.gitBlobSha))fail("unsafe path or hash");
   const source=documents[entry.repository];
   if(typeof source!=="string" || gitBlobSha(source)!==entry.gitBlobSha)fail("provider blob changed");
   let doc;try{doc=JSON.parse(source);}catch{fail("malformed provider JSON");}
   if(JSON.stringify(doc,null,2)+"\n"!==source)fail("noncanonical provider JSON");
   plain(doc,fields,"contract");
   if(doc.schemaVersion!==1 || doc.organization!==lock.organization ||
      doc.repository!==entry.repository ||
      doc.kind!=="PROPOSED_CONTRACT_NOT_IMPLEMENTATION" ||
      doc.hostOracleRepo!=="oreslang-ml-conformance" || doc.hostOracleVerified!==false ||
      doc.guestExecution!=="NOT_EXECUTED" ||
      !Array.isArray(doc.evidence) || doc.evidence.length!==0 ||
      !/^[a-f0-9]{40}$/.test(doc.mainSnapshotSha) ||
      typeof doc.nextGate!=="string" || doc.nextGate.length<60)fail("contract provenance");
   for(const key of ["provides","requires","upstreams","fixtureIds"])
     distinctSorted(doc[key],key);
   if(doc.provides.length!==1 || doc.provides[0]!==roles.get(doc.repository) ||
      JSON.stringify(doc.requires)!==JSON.stringify(needs.get(doc.repository)) ||
      !doc.fixtureIds.length || doc.upstreams.includes(doc.repository))
     fail("wrong interfaces/fixtures");
   // Interface names alone do not establish provider edges. Require each
   // declared interface dependency to name its actual owning repository.
   // This remains a planned dependency, NOT evidence of a compiled import.
   for(const requiredInterface of doc.requires){
     const provider = [...roles.entries()].find(([,id]) => id===requiredInterface)?.[0];
     if(!provider || provider===doc.repository || !doc.upstreams.includes(provider))
       fail("missing upstream owner for required interface");
   }
   satisfied.add(doc.provides[0]);
 }
 if(seen.size!==roles.size || lock.requirements.length!==satisfied.size ||
    lock.requirements.some(id=>!satisfied.has(id)))fail("missing interface");
 // Enforce transitive no-cycle dependency closure and provider-ownership edges.
 for(const [owner,deps] of needs) {
   const own=roles.get(owner);
   if(deps.includes(own))fail("cycle");
   for(const req of deps) {
     const provider=[...roles].find(([_,id])=>id===req)?.[0];
     if(!provider || provider===owner)fail("unknown or self interface");
     if(owner==="oreslang-autograd" && provider!=="oreslang-tensor" ||
        owner==="oreslang-ml" && !["oreslang-tensor","oreslang-autograd"].includes(provider))
       fail("unsupported topology");
   }
 }
 return Object.freeze({status:"CONTRACT_LINKS_ONLY_NOT_GUEST_CONFORMANCE",
  providers:seen.size,interfaces:satisfied.size,hostReferenceRunsNotEvidence:true,
  guestExecution:false,sourceExportAllowed:false,releaseReady:false});
}
export function loadProviderLock(){
 const base=new URL("../contracts/",import.meta.url);
 const read=(p)=>readFileSync(new URL(p,base),"utf8");
 const lock=JSON.parse(read("provider-lock.v1.json"));
 const docs={};
 for(const p of lock.providers) {
   if(!roles.has(p.repository)||p.path!=="contracts/providers/"+p.repository+".v1.json")fail("invalid path");
   docs[p.repository]=read("providers/"+p.repository+".v1.json");
 }
 return {lock,documents:docs};
}
