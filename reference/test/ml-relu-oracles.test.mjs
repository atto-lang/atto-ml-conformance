import test from "node:test";
import assert from "node:assert/strict";

// Independently authored synthetic numeric examples. These are not private
// Oreslang source, private P0 fixture data, guest execution, or release proof.
function relu(x){ if(!Number.isFinite(x))throw Error("nonfinite activation");return Math.max(0,x); }
function reluSlope(x){ if(!Number.isFinite(x))throw Error("nonfinite derivative");return x>0?1:0; }
function train(inputs,targets,learningRate,iterations,initial=[1,0,1,0]) {
  if(!Array.isArray(inputs)||!Array.isArray(targets)||inputs.length!==targets.length||
     inputs.length<1||inputs.length>100||!Number.isFinite(learningRate)||
     learningRate<=0||learningRate>.1||!Number.isSafeInteger(iterations)||
     iterations<1||iterations>1000||!Array.isArray(initial)||initial.length!==4||
     [...inputs,...targets,...initial].some(x=>!Number.isFinite(x)))throw Error("invalid training");
  let [a,b,c,d]=initial;
  function loss(){
    let z=0;for(let j=0;j<inputs.length;j++){
      const diff=c*relu(a*inputs[j]+b)+d-targets[j];z+=diff*diff;
    }return z/inputs.length;
  }
  const before=loss();
  for(let j=0;j<iterations;j++){
    let ga=0,gb=0,gc=0,gd=0;
    for(let i=0;i<inputs.length;i++){
      const x=inputs[i],z=a*x+b,h=relu(z),err=c*h+d-targets[i],g=2*err;
      ga+=g*c*reluSlope(z)*x;gb+=g*c*reluSlope(z);gc+=g*h;gd+=g;
    }
    const k=learningRate/inputs.length;
    a-=k*ga;b-=k*gb;c-=k*gc;d-=k*gd;
    if(![a,b,c,d].every(Number.isFinite))throw Error("nonfinite optimizer state");
  }
  return Object.freeze({before,after:loss(),parameters:Object.freeze([a,b,c,d])});
}
const X=[-3,-1,0,1,2,4],Y=[2,2,2,4,6,10];
test("ReLU positive and negative branches",()=>{assert.equal(relu(-10),0);assert.equal(relu(4.25),4.25)});
test("ReLU zero follows explicitly chosen zero-subgradient",()=>{assert.equal(relu(0),0);assert.equal(reluSlope(0),0)});
test("ReLU nonzero finite gradients",()=>{assert.equal(reluSlope(-2),0);assert.equal(reluSlope(2),1)});
test("Reject NaN/Infinity in activation and derivative",()=>{
  for(const v of [NaN,Infinity,-Infinity]){
    assert.throws(()=>relu(v),/nonfinite/);
    assert.throws(()=>reluSlope(v),/nonfinite/);
  }
});
test("Finite difference matches away from nondifferentiable zero",()=>{
  const h=1e-5;
  for(const x of [-2,1,7]){
    const diff=(relu(x+h)-relu(x-h))/(2*h);
    assert.ok(Math.abs(diff-reluSlope(x))<1e-8);
  }
});
test("Do not falsely equate symmetric finite difference at cusp with chosen subgradient",()=>{
  const h=1e-5,diff=(relu(h)-relu(-h))/(2*h);
  assert.equal(diff,.5);assert.equal(reluSlope(0),0);
});
test("Synthetic 2-layer nonlinear training reduces loss",()=>{
  const m=train(X,Y,.02,700);
  assert.ok(m.before>3);
  assert.ok(m.after<m.before/10000);
});
test("MLP training repeats deterministically",()=>{
  const a=train(X,Y,.02,500),b=train(X,Y,.02,500);
  assert.deepEqual(a,b);
});
test("Invalid batch shape and learning rates fail closed",()=>{
  assert.throws(()=>train(X,[1],.02,10),/invalid training/);
  assert.throws(()=>train(X,Y,0,10),/invalid training/);
  assert.throws(()=>train(X,Y,NaN,10),/invalid training/);
  assert.throws(()=>train(X,Y,.3,10),/invalid training/);
});
test("Reject invalid training parameters, excessive steps and poisoned inputs",()=>{
  assert.throws(()=>train([Infinity],[0],.02,10),/invalid training/);
  assert.throws(()=>train(X,Y,.02,1001),/invalid training/);
  assert.throws(()=>train(X,Y,.02,10,[1,2,3]),/invalid training/);
});
