// Source-free independent scalar/numeric oracle fixture.
// This is JavaScript host reference only; it never claims Oreslang guest execution.
// No code from any private Oreslang repository is copied to this test carrier.
function finite(x, label) {
  if (typeof x !== "number" || !Number.isFinite(x)) throw Error(label + ": finite scalar required");
  return x;
}
// Snapshot canonical numeric arrays without invoking custom iterators, getters,
// inherited slots or Array.map() holes in a host-only reference oracle.
function denseData(array, label, maxLength) {
  if (!Array.isArray(array) || Object.getPrototypeOf(array) !== Array.prototype ||
      array.length > maxLength || Reflect.ownKeys(array).length !== array.length + 1)
    throw Error("invalid " + label);
  const result = [];
  for (let i = 0; i < array.length; i++) {
    const slot = Object.getOwnPropertyDescriptor(array, String(i));
    if (!slot || !Object.hasOwn(slot, "value"))
      throw Error("invalid " + label + " element");
    result.push(slot.value);
  }
  return result;
}
export function checkedNumel(shape, maxElements = 1_000_000) {
  if (!Number.isSafeInteger(maxElements) || maxElements < 0)
    throw Error("invalid shape or bound");
  const dimensions = denseData(shape, "shape", 8);
  for (const d of dimensions)
    if (!Number.isSafeInteger(d) || d < 0) throw Error("invalid dimension");
  // A zero-extent tensor occupies zero elements regardless of where zero
  // appears; validate *all* dimensions before computing nonzero products.
  if (dimensions.includes(0)) return 0;
  let count = 1;
  for (const d of dimensions) {
    if (count > Math.floor(maxElements / d))
      throw Error("shape product overflow or allocation bound");
    count *= d;
  }
  if (count > maxElements) throw Error("shape allocation bound");
  return count;
}
function checkedData(shape, data) {
  const n = checkedNumel(shape);
  if (!Array.isArray(data) || data.length !== n) throw Error("shape/data mismatch");
  return denseData(data, "data", n).map((x, i) => finite(x, "data[" + i + "]"));
}
export function addTensor(shape, left, right) {
  const a = checkedData(shape, left);
  const b = checkedData(shape, right);
  return Object.freeze({shape: Object.freeze(denseData(shape, 'shape', 8)),
    data: Object.freeze(a.map((x, i) => finite(x + b[i], "add result")))});
}
export function matmul2d(leftShape, left, rightShape, right) {
  if (!Array.isArray(leftShape) || leftShape.length !== 2 ||
      !Array.isArray(rightShape) || rightShape.length !== 2)
    throw Error("matmul requires rank-2");
  const [m, k] = denseData(leftShape, 'shape', 8);
  const [k2, n] = denseData(rightShape, 'shape', 8);
  if (k !== k2) throw Error("matmul inner dimension mismatch");
  const a = checkedData(leftShape, left), b = checkedData(rightShape, right);
  checkedNumel([m, n]);
  // Empty output needs no scalar loop. In particular, [huge, 0]
  // otherwise iterates over an adversarially large row count for no work.
  if (m === 0 || n === 0)
    return Object.freeze({shape:Object.freeze([m,n]),data:Object.freeze([])});
  const result = new Array(m * n).fill(0);
  for (let i = 0; i < m; i++)
    for (let j = 0; j < n; j++)
      for (let z = 0; z < k; z++)
        result[i * n + j] = finite(result[i * n + j] + a[i * k + z] * b[z * n + j], "matmul result");
  return Object.freeze({shape: Object.freeze([m, n]), data: Object.freeze(result)});
}
let nextId = 0;
function node(op, value, parents) {
  return Object.freeze({id: ++nextId, op, value: finite(value, op),
    parents: Object.freeze(parents.map(({parent, weight}) => Object.freeze({parent, weight: finite(weight, "weight")})))});
}
export function variable(x) { return node("var", x, []); }
export function add(a, b) {
  if (!a || !b || !Object.isFrozen(a) || !Object.isFrozen(b)) throw Error("invalid graph node");
  return node("add", finite(a.value + b.value, "sum"),
    [{parent: a, weight: 1}, {parent: b, weight: 1}]);
}
export function multiply(a, b) {
  if (!a || !b || !Object.isFrozen(a) || !Object.isFrozen(b)) throw Error("invalid graph node");
  return node("mul", finite(a.value * b.value, "product"),
    [{parent: a, weight: b.value}, {parent: b, weight: a.value}]);
}
// These are host-oracle resource budgets, not compiler/runtime quotas.
const MAX_TAPE_NODES = 100_000;
const MAX_TAPE_EDGES = 200_000;
// Only frozen, own-data records enter the host oracle. A frozen JavaScript
// object may still contain getters or sparse array slots; reading them would
// invoke caller code during an ostensibly independent numerical check.
function ownTapeField(record, field, error) {
  const descriptor = Object.getOwnPropertyDescriptor(record, field);
  if (!descriptor || !Object.hasOwn(descriptor, "value")) throw Error(error);
  return descriptor.value;
}
function snapshotTapeParents(record) {
  if (!record || typeof record !== "object" || !Object.isFrozen(record) ||
      Object.getPrototypeOf(record) !== Object.prototype)
    throw Error("malformed tape node");
  const id = ownTapeField(record, "id", "malformed tape node");
  const value = ownTapeField(record, "value", "malformed tape node");
  const rawParents = ownTapeField(record, "parents", "malformed tape node");
  if (!Number.isSafeInteger(id) || id <= 0 || !Number.isFinite(value) ||
      !Array.isArray(rawParents) || !Object.isFrozen(rawParents))
    throw Error("malformed tape node");
  if (rawParents.length > MAX_TAPE_EDGES) throw Error("tape budget exceeded");
  const edges = denseData(rawParents, "tape parents", MAX_TAPE_EDGES);
  return edges.map((edge) => {
    if (!edge || typeof edge !== "object" || !Object.isFrozen(edge) ||
        Object.getPrototypeOf(edge) !== Object.prototype)
      throw Error("invalid tape edge");
    const parent = ownTapeField(edge, "parent", "invalid tape edge");
    const weight = ownTapeField(edge, "weight", "invalid tape edge");
    if (!Number.isFinite(weight) || !parent || typeof parent !== "object")
      throw Error("invalid tape edge");
    return {parent, weight};
  });
}
export function gradients(output) {
  const visited = new Set(), active = new Set(), topo = [];
  const snapshots = new Map();
  // Iterative postorder protects deep DAGs. Validated, snapped edges ensure
  // second-pass accumulation never re-reads attacker-provided descriptors.
  const stack = [{node: output, nextEdge: 0, edges: null}];
  let traversedEdges = 0;
  while (stack.length) {
    const frame = stack[stack.length - 1], n = frame.node;
    if (frame.edges === null) {
      if (active.has(n)) throw Error("tape cycle");
      if (visited.has(n)) { stack.pop(); continue; }
      if (visited.size + active.size >= MAX_TAPE_NODES)
        throw Error("tape budget exceeded");
      frame.edges = snapshotTapeParents(n);
      snapshots.set(n, frame.edges);
      active.add(n);
    }
    if (frame.nextEdge < frame.edges.length) {
      if (++traversedEdges > MAX_TAPE_EDGES) throw Error("tape budget exceeded");
      const edge = frame.edges[frame.nextEdge++];
      if (active.has(edge.parent)) throw Error("tape cycle");
      if (!visited.has(edge.parent))
        stack.push({node: edge.parent, nextEdge: 0, edges: null});
    } else {
      active.delete(n);
      visited.add(n);
      topo.push(n);
      stack.pop();
    }
  }
  const grads = new Map([[output, 1]]);
  for (const n of topo.reverse()) {
    const g = grads.get(n) || 0;
    for (const edge of snapshots.get(n)) {
      const prev = grads.get(edge.parent) || 0;
      grads.set(edge.parent, finite(prev + g * edge.weight, "gradient accumulation"));
    }
  }
  return grads;
}
export function finiteDifference(f, x, h = 1e-5) {
  finite(x, "x"); finite(h, "h");
  if (h <= 0 || x + h === x || x - h === x) throw Error("invalid finite-difference step");
  return finite((finite(f(x + h), "f+") - finite(f(x - h), "f-")) / (2 * h), "finite-difference result");
}
export function linearSgdEpoch(examples, w, b, learningRate) {
  finite(w, "weight"); finite(b, "bias"); finite(learningRate, "learningRate");
  if (learningRate <= 0) throw Error("invalid SGD configuration");
  // Snapshot exact dense records without invoking an untrusted iterator,
  // per-array map override, or getter-backed slots.
  const rows = denseData(examples, "examples", 10000);
  if (rows.length === 0) throw Error("invalid SGD configuration");
  let loss = 0, dw = 0, db = 0;
  for (const pair of rows) {
    const fields = denseData(pair, "training pair", 2);
    if (fields.length !== 2) throw Error("invalid training pair");
    const [x, y] = fields.map((n) => finite(n, "example"));
    const err = finite(w * x + b - y, "prediction error");
    loss = finite(loss + err * err, "loss");
    dw = finite(dw + 2 * err * x, "weight gradient");
    db = finite(db + 2 * err, "bias gradient");
  }
  const n = rows.length;
  return Object.freeze({loss: loss / n,
    w: finite(w - learningRate * dw / n, "updated weight"),
    b: finite(b - learningRate * db / n, "updated bias")});
}
