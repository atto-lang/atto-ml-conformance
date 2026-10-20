#!/usr/bin/env node
// Opt-in metadata audit only, never source or release evidence.
import {readFileSync} from "node:fs";
import {auditWorkspaceMetadata, githubMetadataReader} from "../src/workspace-metadata-audit.mjs";
try {
 if(process.argv.length!==2)throw Error("usage: node bin/audit-workspace-metadata.mjs");
 const path=new URL("../manifests/p0-workspace.json",import.meta.url);
 const workspace=JSON.parse(readFileSync(path,"utf8"));
 const read=githubMetadataReader(process.env.ORESLANG_REPOSITORY_READ_TOKEN);
 const result=await auditWorkspaceMetadata(workspace,read);
 console.log(JSON.stringify(result,null,2));
} catch(e) {
 console.error(String(e.message));
 process.exitCode=2;
}
