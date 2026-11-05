import test from 'node:test';
import assert from 'node:assert/strict';
import {addTensor, matmul2d, linearSgdEpoch} from '../ml-oracles.mjs';

test('small complete matrix shape cross-product agrees with independent CPU oracle', () => {
  let cases = 0;
  for (let m = 0; m < 4; m++) for (let k = 0; k < 4; k++) for (let n = 0; n < 4; n++) {
    const left = Array.from({length: m*k}, (_,i) => (i % 7) - 3);
    const right = Array.from({length: k*n}, (_,i) => (i % 5) - 2);
    const expected = [];
    for (let i=0; i<m; i++) for (let j=0; j<n; j++) {
      let sum = 0;
      for (let z=0; z<k; z++) sum += left[i*k+z]*right[z*n+j];
      expected.push(sum);
    }
    const actual = matmul2d([m,k], left, [k,n], right);
    assert.deepEqual(actual.shape, [m,n]);
    assert.deepEqual(actual.data, expected);
    assert.ok(Object.isFrozen(actual.data) && Object.isFrozen(actual.shape));
    cases++;
  }
  assert.equal(cases, 64);
});
test('scalar, empty, and rectangular tensor additions preserve shape and values', () => {
  for (const shape of [[], [0], [2], [2,3], [2,0,3]]) {
    const n = shape.reduce((acc,x) => acc*x, 1);
    const left = Array.from({length:n}, (_,i)=>i-2);
    const right = Array.from({length:n}, (_,i)=>2*i);
    const result = addTensor(shape,left,right);
    assert.deepEqual(result.shape,shape);
    assert.deepEqual(result.data,left.map((x,i)=>x+right[i]));
  }
});
test('SGD single-epoch loss and update match independent gradients', () => {
  const examples=[[0,1],[1,3],[2,5]], w=0.5,b=-1, lr=0.125;
  let loss=0, dw=0, db=0;
  for (const [x,y] of examples) {
    const error=w*x+b-y;
    loss+=error*error; dw+=2*error*x; db+=2*error;
  }
  const result=linearSgdEpoch(examples,w,b,lr);
  assert.ok(Math.abs(result.loss-loss/examples.length)<1e-12);
  assert.ok(Math.abs(result.w-(w-lr*dw/examples.length))<1e-12);
  assert.ok(Math.abs(result.b-(b-lr*db/examples.length))<1e-12);
});
