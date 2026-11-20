import test from 'node:test';
import assert from 'node:assert/strict';
import { checkedNumel, addTensor, linearSgdEpoch } from '../ml-oracles.mjs';

test('sparse or embellished shape arrays are denied before element arithmetic', () => {
  assert.throws(() => checkedNumel(new Array(2)), /invalid shape/);
  const shape = [2];
  shape.extra = 7;
  assert.throws(() => checkedNumel(shape), /invalid shape/);
});

test('shape element getters are not invoked by the independent oracle', () => {
  let reads = 0;
  const shape = [2];
  Object.defineProperty(shape, '0', { enumerable: true, get() { reads++; throw Error('hostile getter'); } });
  assert.throws(() => checkedNumel(shape), /invalid shape element/);
  assert.equal(reads, 0);
});

test('tensor and SGD inputs reject holes and getter-backed rows', () => {
  assert.throws(() => addTensor([2], [1, ,], [3, 4]), /invalid data/);
  let reads = 0;
  const examples = [[0, 1]];
  Object.defineProperty(examples, '0', { enumerable: true, get() { reads++; throw Error('hostile row'); } });
  assert.throws(() => linearSgdEpoch(examples, 0, 0, 0.1), /invalid examples element/);
  assert.equal(reads, 0);
});
