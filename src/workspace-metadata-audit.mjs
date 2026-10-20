// Read-only GitHub metadata verification: no Git blobs, trees, checkout,
// private source, secrets, runner artifacts or cross-organization exports.
const org = "ores-truffle-oreslang";
const ids = Object.freeze({
  "oreslang-tensor": 1423912926,
  "oreslang-autograd": 1423913203,
  "oreslang-ml": 1423913534
});
const names = Object.keys(ids).sort();
const sha40 = /^[a-f0-9]{40}$/;
export async function auditWorkspaceMetadata(manifest, readJson) {
  if (!manifest || typeof manifest !== "object" || Array.isArray(manifest) ||
      manifest.schema_version !== "oreslang-ml-workspace/v1" ||
      manifest.compiler_artifact !== "NOT_PINNED" ||
      typeof manifest.source_state !== "string" ||
      !manifest.source_state.includes("NOT_GUEST_TESTED") ||
      typeof readJson !== "function") throw Error("WORKSPACE_METADATA_DENIED: admission");
  const commits = manifest.repositories, trees = manifest.source_trees;
  for(const obj of [commits,trees]) {
    if(!obj || typeof obj !== "object" || Array.isArray(obj) ||
      JSON.stringify(Object.keys(obj).sort()) !== JSON.stringify(names))
      throw Error("WORKSPACE_METADATA_DENIED: provider identity set");
  }
  for(const n of names) {
    if(!sha40.test(commits[n]) || !sha40.test(trees[n]) || commits[n] === trees[n])
      throw Error("WORKSPACE_METADATA_DENIED: immutable commit and tree pins");
  }
  const audited=[];
  for(const name of names) {
    const route="/repos/"+org+"/"+name;
    const info=await readJson(route);
    if(!info || info.id !== ids[name] || info.full_name !== org+"/"+name ||
       info.private !== true || info.archived !== false || info.default_branch !== "main")
      throw Error("WORKSPACE_METADATA_DENIED: repository identity "+name);
    const record=await readJson(route+"/git/commits/"+commits[name]);
    if(!record || record.sha !== commits[name] || record.tree?.sha !== trees[name])
      throw Error("WORKSPACE_METADATA_DENIED: missing commit or tree mismatch "+name);
    audited.push({repository:name,repositoryId:ids[name],commit:commits[name],tree:trees[name]});
  }
  return Object.freeze({status:"METADATA_COMMIT_TREE_MATCH_NOT_GUEST_PROOF",
     sourceFilesFetched:0,sourceExportAuthorized:false,guestExecution:false,
     releaseReady:false,repositoriesChecked:audited.length,observed:audited});
}
export function githubMetadataReader(token, fetchImpl=globalThis.fetch) {
  if(typeof token!=="string" || token.length<8 || token.trim()!==token ||
     /[\r\n]/.test(token) || typeof fetchImpl!=="function")
    throw Error("WORKSPACE_METADATA_DENIED: explicit read-only token required");
  return async path=>{
    if(typeof path!=="string" || !/^\/repos\/ores-truffle-oreslang\/oreslang-(?:tensor|autograd|ml)(?:\/git\/commits\/[a-f0-9]{40})?$/.test(path))
      throw Error("WORKSPACE_METADATA_DENIED: API path");
    const response=await fetchImpl("https://api.github.com"+path,{
       method:"GET",redirect:"error",signal:AbortSignal.timeout(15000),
       headers:{Accept:"application/vnd.github+json",
         "X-GitHub-Api-Version":"2022-11-28",Authorization:"Bearer "+token}
    });
    if(!response?.ok)throw Error("WORKSPACE_METADATA_DENIED: GitHub HTTP "+response?.status);
    const bytes=await response.text();
    if(bytes.length>1_000_000)throw Error("WORKSPACE_METADATA_DENIED: oversized response");
    return JSON.parse(bytes);
  };
}
