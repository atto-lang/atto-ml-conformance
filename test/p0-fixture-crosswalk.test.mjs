import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {checkedNumel,addTensor,matmul2d,variable,add,multiply,gradients,linearSgdEpoch} from "../reference/ml-oracles.mjs";

const read=p=>JSON.parse(readFileSync(new URL("../"+p,import.meta.url),"utf8"));
const original=read("fixtures/p0-v1.json"), crosswalk=read("integration/p0-fixture-crosswalk.v1.json");
const providerLock=read("contracts/provider-lock.v1.json"), workspace=read("manifests/p0-workspace.json");
const cases=new Map(original.cases.map(c=>[c.id,c]));
const near=(a,b,epsilon=1e-6)=>assert.ok(Math.abs(a-b)<=epsilon,String(a)+" != "+String(b));

test("crosswalk has five canonical interface mappings and no fabricated shape case",()=>{
 assert.equal(crosswalk.schemaVersion,1);
 assert.equal(crosswalk.kind,"HOST_ORACLE_FIXTURE_CROSSWALK_NOT_GUEST_EXECUTION");
 assert.equal(crosswalk.guestExecuted,false);
 assert.equal(crosswalk.mapping.length,5);
 assert.equal(crosswalk.mapping.filter(m=>m.p0CaseId===null).length,1);
 assert.equal(crosswalk.mapping.find(m=>m.contractFixtureId==="tensor/shape/v1").coverage,"NOT_EXPLICIT_P0_CASE");
 const names=crosswalk.mapping.map(m=>m.contractFixtureId);
 assert.equal(new Set(names).size,names.length);
 assert.deepEqual([...names].sort(),names);
 assert.equal(new Set(original.cases.map(c=>c.id)).size,10);
 assert.equal(crosswalk.p0SourceFixtureCount,original.cases.length);
});
test("covered P0 IDs exist and unsupported P0 cases are disclosed",()=>{
 const mapped=new Set();
 for(const m of crosswalk.mapping) {
   assert.ok(providerLock.requirements.includes(m.interfaceId));
   if(m.p0CaseId===null)continue;
   assert.equal(m.coverage,"P0_SCALAR_REFERENCE_ONLY");
   assert.ok(cases.has(m.p0CaseId));
   assert.ok(!mapped.has(m.p0CaseId));
   mapped.add(m.p0CaseId);
 }
 assert.deepEqual([...cases.keys()].filter(id=>!mapped.has(id)).sort(),crosswalk.p0OnlyCases);
});
test("independent JavaScript add oracle agrees with the P0 Python fixture",()=>{
 const c=cases.get("tensor/add-2x2");
 assert.deepEqual(addTensor(c.left.shape,c.left.values,c.right.values).data,c.expected);
 assert.equal(checkedNumel(c.left.shape),c.expected.length);
});
test("independent JavaScript matmul oracle agrees with the P0 Python fixture",()=>{
 const c=cases.get("tensor/matmul-2x2");
 const r=matmul2d(c.left.shape,c.left.values,c.right.shape,c.right.values);
 assert.deepEqual(r.data,c.expected);
});
test("P0-only ReLU and sum cases remain disclosed and numerically correct",()=>{
 const relu=cases.get("tensor/relu-4"),sum=cases.get("tensor/sum-2x2");
 assert.deepEqual(relu.input.values.map(v=>Math.max(0,v)),relu.expected);
 assert.equal(sum.input.values.reduce((a,b)=>a+b,0),sum.expected);
});
test("diamond tape value and leaf gradient agree with P0 fixture",()=>{
 const c=cases.get("autograd/diamond");
 const x=variable(c.leaf_values[0]),sq=multiply(x,x),out=add(sq,x);
 assert.equal(out.value,c.expected_value);
 assert.equal(gradients(out).get(x),c.expected_grads[0]);
 assert.equal(c.expected_grads[1],1);assert.equal(c.expected_grads[2],1);
});
test("independent 500-step SGD oracle meets P0 training tolerances",()=>{
 const c=cases.get("ml/affine-500"),samples=c.inputs.map((x,i)=>[x,c.targets[i]]);
 let w=c.initial_weight,b=c.initial_bias;
 for(let i=0;i<c.steps;i++){const next=linearSgdEpoch(samples,w,b,c.learning_rate);w=next.w;b=next.b;}
 const final=linearSgdEpoch(samples,w,b,c.learning_rate);
 near(w,c.expected_weight,1e-4);near(b,c.expected_bias,1e-4);
 assert.ok(final.loss<=c.max_loss);
});
test("workspace requires exact source commits and does not attest a compiler",()=>{
 assert.equal(workspace.schema_version,"oreslang-ml-workspace/v1");
 assert.equal(workspace.compiler_artifact,"NOT_PINNED");
 assert.match(workspace.source_state,/NOT_GUEST_TESTED/);
 assert.deepEqual(Object.keys(workspace.repositories).sort(),
   ["oreslang-autograd","oreslang-ml","oreslang-tensor"]);
 for(const sha of Object.values(workspace.repositories))assert.match(sha,/^[a-f0-9]{40}$/);
 assert.equal(providerLock.guestEvidence,"NOT_EXECUTED");
 assert.equal(providerLock.sourceExportsAllowed,false);
});
test("tampered expected output is not accepted by the host oracle",()=>{
 const c=cases.get("tensor/matmul-2x2"),copy=[...c.expected];copy[0]+=100;
 assert.notDeepEqual(matmul2d(c.left.shape,c.left.values,c.right.shape,c.right.values).data,copy);
});

test("new P0 ReLU cases record active/inactive/zero subgradient convention without v1 promotion",()=>{
 for(const [id,expected] of [["autograd/relu-active",[1,1]],["autograd/relu-inactive",[0,1]],["autograd/relu-zero",[0,1]]]){
  const c=cases.get(id);
  assert.equal(c.kind,"autograd_scalar");
  const x=c.leaf_values[0],val=Math.max(0,x),g=x>0?1:0;
  assert.equal(val,c.expected_value);
  assert.deepEqual([g,1],c.expected_grads);
  assert.deepEqual(expected,c.expected_grads);
  assert.ok(crosswalk.p0OnlyCases.includes(id));
 }
});
test("new two-layer ReLU reference improves MSE without asserting guest integration",()=>{
 const c=cases.get("ml/two-layer-relu-500");
 assert.equal(c.kind,"mlp_relu_train");
 const [xs,ys]=[c.inputs,c.targets];
 let [w1,b1,w2,b2]=c.initial_parameters;
 const loss=()=>xs.reduce((sum,x,i)=>{
  const error=w2*Math.max(0,w1*x+b1)+b2-ys[i];
  return sum+error*error;
 },0)/xs.length;
 const initial=loss();
 for(let iteration=0;iteration<c.steps;iteration++){
  let dw1=0,db1=0,dw2=0,db2=0;
  for(let i=0;i<xs.length;i++){
   const x=xs[i],z=w1*x+b1,h=Math.max(0,z),err=w2*h+b2-ys[i],up=2*err;
   dw2+=up*h;db2+=up;
   if(z>0){dw1+=up*w2*x;db1+=up*w2;}
  }
  const step=c.learning_rate/xs.length;
  w1-=step*dw1;b1-=step*db1;w2-=step*dw2;b2-=step*db2;
  assert.ok([w1,b1,w2,b2].every(Number.isFinite));
 }
 assert.ok(initial>=c.minimum_initial_loss);
 assert.ok(loss()<c.max_loss);
 assert.ok(crosswalk.p0OnlyCases.includes(c.id));
});
