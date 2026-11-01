import test from "node:test";
import assert from "node:assert/strict";
import {checkedNumel,addTensor,matmul2d,variable,add,multiply,gradients,finiteDifference,linearSgdEpoch} from "../ml-oracles.mjs";

test("scalar tensor rank zero has one element",()=>assert.equal(checkedNumel([]),1));
test("zero-length dimensions have zero elements",()=>assert.equal(checkedNumel([3,0,4]),0));
test("zero-extent numel is order-independent, even with other large safe dimensions",()=>{
 const big=Number.MAX_SAFE_INTEGER;
 for(const shape of [[big,0],[0,big],[2,big,0],[0,2,big],[big,2,0]]){
  assert.equal(checkedNumel(shape,1),0,JSON.stringify(shape));
 }
 assert.throws(()=>checkedNumel([0,-1]),/invalid dimension/);
 assert.throws(()=>checkedNumel([0,1.5]),/invalid dimension/);
 assert.throws(()=>checkedNumel([0,Number.MAX_SAFE_INTEGER+1]),/invalid dimension/);
 assert.throws(()=>checkedNumel([big,2]),/overflow/);
});
test("checked row-major product",()=>assert.equal(checkedNumel([2,3,4]),24));
test("reject negative dimension",()=>assert.throws(()=>checkedNumel([-1]),/invalid dimension/));
test("reject fractional dimension",()=>assert.throws(()=>checkedNumel([1.25]),/invalid dimension/));
test("reject unsafe numeric dimension",()=>assert.throws(()=>checkedNumel([Number.MAX_SAFE_INTEGER+1]),/invalid dimension/));
test("reject shape product overflow and over-allocation",()=>assert.throws(()=>checkedNumel([1000000,1000000]),/overflow/));
test("reject excessive tensor rank",()=>assert.throws(()=>checkedNumel(new Array(9).fill(1)),/invalid shape/));
test("tensor add is elementwise and allocates fresh result",()=>{
 const a=[1,2,3],b=[4,5,6],out=addTensor([3],a,b);
 assert.deepEqual(out.data,[5,7,9]);a[0]=99;b[0]=99;assert.equal(out.data[0],5);
 assert.ok(Object.isFrozen(out.data));assert.ok(Object.isFrozen(out.shape));
});
test("tensor add refuses dimension/data mismatch",()=>assert.throws(()=>addTensor([2],[1],[2,3]),/shape\/data mismatch/));
test("tensor add refuses nonfinite data",()=>assert.throws(()=>addTensor([1],[Infinity],[1]),/finite scalar/));
test("tensor add refuses arithmetic overflow",()=>assert.throws(()=>addTensor([1],[1e308],[1e308]),/finite scalar/));
test("matmul rank-two row-major CPU oracle",()=>{
 const out=matmul2d([2,3],[1,2,3,4,5,6],[3,2],[7,8,9,10,11,12]);
 assert.deepEqual(out.shape,[2,2]);assert.deepEqual(out.data,[58,64,139,154]);
});
test("matmul rejects inner dimension mismatch",()=>assert.throws(()=>matmul2d([1,2],[1,2],[3,1],[1,2,3]),/inner dimension mismatch/));
test("matmul rejects invalid rank",()=>assert.throws(()=>matmul2d([3],[1,2,3],[3,1],[1,2,3]),/rank-2/));
test("matmul zero-width shared dimension yields zeros",()=>{
 const out=matmul2d([2,0],[],[0,3],[]);
 assert.deepEqual(out.data,[0,0,0,0,0,0]);
});
test("reverse-mode scalar derivative x*x + x",()=>{
 const x=variable(3),y=add(multiply(x,x),x);
 const g=gradients(y);
 assert.equal(y.value,12);assert.equal(g.get(x),7);
});
test("reverse-mode shared subgraph accumulates both paths",()=>{
 const x=variable(2),d=multiply(x,x),y=add(d,d);
 assert.equal(gradients(y).get(x),8);
});
test("saved forward values and edge lists cannot mutate",()=>{
 const x=variable(2),y=multiply(x,x);assert.ok(Object.isFrozen(x));
 assert.ok(Object.isFrozen(y.parents));assert.ok(Object.isFrozen(y.parents[0]));
 assert.equal(gradients(y).get(x),4);
});
test("forged cyclic tape rejected",()=>{
 const bad={id:993,value:1,parents:[]};
 bad.parents.push(Object.freeze({parent:bad,weight:1}));
 Object.freeze(bad.parents);Object.freeze(bad);
 assert.throws(()=>gradients(bad),/tape cycle/);
});
test("malformed tape rejected",()=>assert.throws(()=>gradients({value:2,parents:[]}),/malformed tape node/));
test("analytic reverse derivative agrees with independent central difference",()=>{
 const x=variable(1.25),y=multiply(multiply(x,x),x);
 const analytic=gradients(y).get(x),fd=finiteDifference(t=>t*t*t,1.25);
 assert.ok(Math.abs(analytic-fd)<1e-7);
});
test("invalid finite-difference step rejected",()=>assert.throws(()=>finiteDifference(x=>x*x,1,0),/invalid finite-difference step/));
test("non-finite oracle response rejected",()=>assert.throws(()=>finiteDifference(()=>Infinity,1),/finite scalar/));
test("SGD decreases reference linear regression loss",()=>{
 const data=[[0,1],[1,3],[2,5],[3,7]],lr=.05;
 let w=0,b=0,first=linearSgdEpoch(data,w,b,lr).loss,last=first;
 for(let i=0;i<200;i++){const r=linearSgdEpoch(data,w,b,lr);w=r.w;b=r.b;last=linearSgdEpoch(data,w,b,lr).loss;}
 assert.ok(last<first/100);
 assert.ok(Math.abs(w-2)<.15);
 assert.ok(Math.abs(b-1)<.3);
});
test("SGD refuses NaN or invalid learning rate",()=>{
 assert.throws(()=>linearSgdEpoch([[0,1]],0,0,0),/invalid SGD/);
 assert.throws(()=>linearSgdEpoch([[NaN,1]],0,0,.1),/finite scalar/);
});

test("zero extents are order-independent after validating every dimension",()=>{
 assert.equal(checkedNumel([Number.MAX_SAFE_INTEGER,0]),0);
 assert.equal(checkedNumel([0,Number.MAX_SAFE_INTEGER]),0);
 assert.equal(checkedNumel([1000001,0],1),0);
 assert.throws(()=>checkedNumel([0,-1]),/invalid dimension/);
 assert.throws(()=>checkedNumel([0,1.5]),/invalid dimension/);
 const out=addTensor([Number.MAX_SAFE_INTEGER,0],[],[]);
 assert.deepEqual(out.shape,[Number.MAX_SAFE_INTEGER,0]);
 assert.deepEqual(out.data,[]);
});

test("tensor shape and data admission rejects sparse and accessor-backed arrays without running getters",()=>{
 let reads=0;
 const badShape=[2];
 Object.defineProperty(badShape,"0",{enumerable:true,get(){reads++;return 2;}});
 assert.throws(()=>checkedNumel(badShape),/invalid shape element/);
 assert.equal(reads,0);
 const badData=[1,2];
 Object.defineProperty(badData,"0",{enumerable:true,get(){reads++;return 1;}});
 assert.throws(()=>addTensor([2],badData,[3,4]),/invalid data element/);
 assert.equal(reads,0);
 assert.throws(()=>addTensor([2],new Array(2),[3,4]),/invalid data/);
 const shape=[2];
 Object.defineProperty(shape,Symbol.iterator,{value:function*(){reads++;yield 2;}});
 assert.throws(()=>checkedNumel(shape),/invalid shape/);
 assert.equal(reads,0);
});

test("empty-result matmul avoids looping an enormous zero-width row count",()=>{
  const r=matmul2d([Number.MAX_SAFE_INTEGER,0],[],[0,0],[]);
  assert.deepEqual(r.shape,[Number.MAX_SAFE_INTEGER,0]);
  assert.deepEqual(r.data,[]);
  assert.ok(Object.isFrozen(r.shape)&&Object.isFrozen(r.data));
});

test("deep tapes use iterative traversal while retaining shared-edge gradient fan-in",()=>{
  const leaf=variable(1), shared=variable(0);
  let tip=leaf;
  for(let i=0;i<20000;i++) tip=add(tip,shared);
  const g=gradients(tip);
  assert.equal(g.get(leaf),1);
  assert.equal(g.get(shared),20000);
});
test("oversized hostile frozen tape is rejected before traversing edges",()=>{
  const leaf=variable(1), edge=Object.freeze({parent:leaf,weight:1});
  const parents=Object.freeze(new Array(200001).fill(edge));
  const root=Object.freeze({id:999999,value:1,parents});
  assert.throws(()=>gradients(root),/tape budget exceeded/);
});

test("SGD input admission does not execute array getters, custom maps or iterators",()=>{
  let invoked=0;
  const badRows=[[1,2]];
  Object.defineProperty(badRows,"0",{configurable:true,get(){invoked++;return [1,2];}});
  assert.throws(()=>linearSgdEpoch(badRows,0,0,.1),/invalid examples element/);
  const badPair=[1,2];
  Object.defineProperty(badPair,"1",{configurable:true,get(){invoked++;return 2;}});
  assert.throws(()=>linearSgdEpoch([badPair],0,0,.1),/invalid training pair element/);
  const oddPair=[1,2];
  oddPair.map=()=>{invoked++;return [999,999];};
  assert.throws(()=>linearSgdEpoch([oddPair],0,0,.1),/invalid training pair/);
  const customIterator=[[1,2]];
  Object.defineProperty(customIterator,Symbol.iterator,{value:function*(){invoked++;yield [1,2];}});
  assert.throws(()=>linearSgdEpoch(customIterator,0,0,.1),/invalid examples/);
  assert.equal(invoked,0);
});

test("frozen accessor-backed tape nodes and edges cannot invoke getters",()=>{
  let invoked=0;
  const normal=variable(2);
  const badValue={id:994,parents:Object.freeze([])};
  Object.defineProperty(badValue,"value",{enumerable:true,get(){invoked++;return 9;}});
  Object.freeze(badValue);
  assert.throws(()=>gradients(badValue),/malformed tape node/);
  const badParents={id:995,value:1};
  Object.defineProperty(badParents,"parents",{enumerable:true,get(){invoked++;return [];}});
  Object.freeze(badParents);
  assert.throws(()=>gradients(badParents),/malformed tape node/);
  const badEdge={parent:normal};
  Object.defineProperty(badEdge,"weight",{enumerable:true,get(){invoked++;return 1;}});
  Object.freeze(badEdge);
  const root=Object.freeze({id:996,value:1,parents:Object.freeze([badEdge])});
  assert.throws(()=>gradients(root),/invalid tape edge/);
  assert.equal(invoked,0);
});
test("frozen sparse or accessor-backed parent arrays fail closed",()=>{
  const leaf=variable(1);
  const sparse=Object.freeze(new Array(2));
  const root=Object.freeze({id:997,value:1,parents:sparse});
  assert.throws(()=>gradients(root),/invalid tape parents/);
  let called=0;
  const edges=[Object.freeze({parent:leaf,weight:1})];
  Object.defineProperty(edges,"0",{get(){called++;return null;}});
  const second=Object.freeze({id:998,value:1,parents:Object.freeze(edges)});
  assert.throws(()=>gradients(second),/invalid tape parents element/);
  assert.equal(called,0);
});
test("host oracle refuses exotic tape node and edge prototypes",()=>{
  const leaf=variable(1);
  const node=Object.freeze(Object.assign(Object.create({trusted:true}),{
    id:999,value:1,parents:Object.freeze([])}));
  assert.throws(()=>gradients(node),/malformed tape node/);
  const edge=Object.freeze(Object.assign(Object.create({trusted:true}),{parent:leaf,weight:1}));
  const root=Object.freeze({id:1000,value:1,parents:Object.freeze([edge])});
  assert.throws(()=>gradients(root),/invalid tape edge/);
});

test("scalar graph constructors reject frozen accessor nodes without invoking them",()=>{
  let fired=0;
  const forged={id:777,parents:Object.freeze([])};
  Object.defineProperty(forged,"value",{get(){fired++;return 42;}});
  Object.freeze(forged);
  const safe=variable(1);
  assert.throws(()=>add(safe,forged),/malformed tape node|invalid graph node/);
  assert.throws(()=>add(forged,safe),/malformed tape node|invalid graph node/);
  assert.throws(()=>multiply(safe,forged),/malformed tape node|invalid graph node/);
  assert.throws(()=>multiply(forged,safe),/malformed tape node|invalid graph node/);
  assert.equal(fired,0);
});
test("graph constructors reject malformed frozen parent data",()=>{
  const valid=variable(1);
  const bad=Object.freeze({id:778,value:2,parents:Object.freeze(new Array(1))});
  assert.throws(()=>add(valid,bad),/invalid tape parents/);
  assert.throws(()=>multiply(valid,bad),/invalid tape parents/);
  const odd=Object.freeze(Object.assign(Object.create({untrusted:true}),{
    id:779,value:2,parents:Object.freeze([])}));
  assert.throws(()=>add(odd,valid),/malformed tape node/);
});
test("independent dual-number derivatives match random shared scalar DAGs",()=>{
  let state=0xabc123ef;
  const next=()=>{state ^= state << 13;state ^= state >>> 17;state ^= state << 5;return (state>>>0)/4294967296;};
  for(let trial=0;trial<2048;trial++){
    const leaves=Array.from({length:5},()=>variable((next()-.5)*2));
    let tape=leaves[Math.floor(next()*leaves.length)];
    let forward={value:tape.value,partials:leaves.map(x=>x===tape?1:0)};
    for(let step=0;step<6;step++){
      const b=leaves[Math.floor(next()*leaves.length)];
      const bv=b.value, isAdd=next()<.5;
      if(isAdd){
        tape=add(tape,b);
        forward={value:forward.value+bv,
          partials:forward.partials.map((d,j)=>d+(leaves[j]===b?1:0))};
      }else{
        tape=multiply(tape,b);
        forward={value:forward.value*bv,
          partials:forward.partials.map((d,j)=>d*bv+forward.value*(leaves[j]===b?1:0))};
      }
    }
    const reverse=gradients(tape);
    for(let j=0;j<leaves.length;j++){
      const got=reverse.get(leaves[j])||0,expected=forward.partials[j];
      assert.ok(Math.abs(got-expected)<1e-9*Math.max(1,Math.abs(expected)),
        "trial="+trial+" leaf="+j+" reverse="+got+" dual="+expected);
    }
  }
});

test("randomized checked shape products agree with independent BigInt algebra",()=>{
  let state=0x76543210;
  const next=()=>{state ^=state<<13;state ^=state>>>17;state ^=state<<5;return state>>>0;};
  for(let trial=0;trial<4096;trial++){
    const shape=Array.from({length:next()%6},()=>next()%1001);
    const bound=next()%1000001;
    const exact=shape.reduce((p,d)=>p*BigInt(d),1n);
    const shouldFit=exact<=BigInt(bound);
    if(shouldFit){
      assert.equal(checkedNumel(shape,bound),Number(exact));
    }else{
      assert.throws(()=>checkedNumel(shape,bound),/overflow|bound/);
    }
  }
});
test("randomized matrix multiplication matches independent dot-product construction",()=>{
  let state=0x32106543;
  const next=()=>{state ^=state<<13;state ^=state>>>17;state ^=state<<5;return state>>>0;};
  for(let trial=0;trial<1024;trial++){
    const m=next()%5,k=next()%5,n=next()%5;
    const left=Array.from({length:m*k},()=>((next()%31)-15));
    const right=Array.from({length:k*n},()=>((next()%31)-15));
    const expected=Array.from({length:m*n},(_,slot)=>{
      const i=Math.floor(slot/n),j=slot%n;
      return Array.from({length:k},(_,p)=>left[i*k+p]*right[p*n+j])
        .reduce((a,b)=>a+b,0);
    });
    const out=matmul2d([m,k],left,[k,n],right);
    assert.deepEqual(out.shape,[m,n]);
    assert.deepEqual(out.data,expected);
    assert.ok(Object.isFrozen(out.shape)&&Object.isFrozen(out.data));
  }
});
test("randomized SGD updates match independent batch-gradient equations",()=>{
  let state=0x496bf321;
  const next=()=>{state ^=state<<13;state ^=state>>>17;state ^=state<<5;return (state>>>0)/4294967296;};
  for(let trial=0;trial<1024;trial++){
    const n=1+Math.floor(next()*8);
    const pairs=Array.from({length:n},()=>[(next()-.5)*4,(next()-.5)*4]);
    const w=(next()-.5)*4,b=(next()-.5)*4,rate=.01+next()*.1;
    const error=pairs.map(([x,y])=>w*x+b-y);
    const mean=(values)=>values.reduce((a,v)=>a+v,0)/n;
    const loss=mean(error.map(e=>e*e));
    const dw=mean(error.map((e,i)=>2*e*pairs[i][0]));
    const db=mean(error.map(e=>2*e));
    const actual=linearSgdEpoch(pairs,w,b,rate);
    assert.ok(Math.abs(actual.loss-loss)<1e-11);
    assert.ok(Math.abs(actual.w-(w-rate*dw))<1e-11);
    assert.ok(Math.abs(actual.b-(b-rate*db))<1e-11);
  }
});
test("randomized finite differences agree with analytic cubic derivatives",()=>{
  let state=0x1f2e3d4c;
  const next=()=>{state ^=state<<13;state ^=state>>>17;state ^=state<<5;return (state>>>0)/4294967296;};
  for(let trial=0;trial<1024;trial++){
    const x=(next()-.5)*3,a=(next()-.5)*2,b=(next()-.5)*2,c=(next()-.5)*2;
    const approx=finiteDifference(v=>a*v*v*v+b*v*v+c,x);
    const analytic=3*a*x*x+2*b*x;
    assert.ok(Math.abs(approx-analytic)<1e-8);
  }
});
