// Source-free independent scalar/numeric oracle fixture.
// This is JavaScript host reference only; it never claims Oreslang guest execution.
// No code from any private Oreslang repository is copied to this test carrier.
function finite(x, label) {
  if (typeof x !== "number" || !Number.isFinite(x)) throw Error(label + ": finite scalar required");
  return x;
}
export function checkedNumel(shape, maxElements = 1_000_000) {
  if (!Array.isArray(shape) || shape.length > 8 ||
      !Number.isSafeInteger(maxElements) || maxElements < 0)
    throw Error("invalid shape or bound");
  let count = 1;
  for (const d of shape) {
    if (!Number.isSafeInteger(d) || d < 0) throw Error("invalid dimension");
    if (count !== 0 && d !== 0 && count > Math.floor(maxElements / d))
      throw Error("shape product overflow or allocation bound");
    count *= d;
  }
  if (count > maxElements) throw Error("shape allocation bound");
  return count;
}
function checkedData(shape, data) {
  const n = checkedNumel(shape);
  if (!Array.isArray(data) || data.length !== n) throw Error("shape/data mismatch");
  return data.map((x, i) => finite(x, "data[" + i + "]"));
}
export function addTensor(shape, left, right) {
  const a = checkedData(shape, left);
  const b = checkedData(shape, right);
  return Object.freeze({shape: Object.freeze([...shape]),
    data: Object.freeze(a.map((x, i) => finite(x + b[i], "add result")))});
}
export function matmul2d(leftShape, left, rightShape, right) {
  if (!Array.isArray(leftShape) || leftShape.length !== 2 ||
      !Array.isArray(rightShape) || rightShape.length !== 2)
    throw Error("matmul requires rank-2");
  const [m, k] = leftShape, [k2, n] = rightShape;
  if (k !== k2) throw Error("matmul inner dimension mismatch");
  const a = checkedData(leftShape, left), b = checkedData(rightShape, right);
  checkedNumel([m, n]);
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
export function gradients(output) {
  const visited = new Set(), active = new Set(), topo = [];
  function visit(n) {
    if (!n || !Number.isSafeInteger(n.id) || !Array.isArray(n.parents) ||
        !Object.isFrozen(n) || !Object.isFrozen(n.parents) || !Number.isFinite(n.value))
      throw Error("malformed tape node");
    if (active.has(n)) throw Error("tape cycle");
    if (visited.has(n)) return;
    active.add(n);
    for (const edge of n.parents) {
      if (!edge || !Object.isFrozen(edge) || !Number.isFinite(edge.weight))
        throw Error("invalid tape edge");
      visit(edge.parent);
    }
    active.delete(n); visited.add(n); topo.push(n);
  }
  visit(output);
  const grads = new Map([[output, 1]]);
  for (const n of topo.reverse()) {
    const g = grads.get(n) || 0;
    for (const edge of n.parents) {
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
  if (learningRate <= 0 || !Array.isArray(examples) || examples.length === 0 ||
      examples.length > 10000) throw Error("invalid SGD configuration");
  let loss = 0, dw = 0, db = 0;
  for (const pair of examples) {
    if (!Array.isArray(pair) || pair.length !== 2) throw Error("invalid training pair");
    const [x, y] = pair.map((n) => finite(n, "example"));
    const err = finite(w * x + b - y, "prediction error");
    loss = finite(loss + err * err, "loss");
    dw = finite(dw + 2 * err * x, "weight gradient");
    db = finite(db + 2 * err, "bias gradient");
  }
  const n = examples.length;
  return Object.freeze({loss: loss / n,
    w: finite(w - learningRate * dw / n, "updated weight"),
    b: finite(b - learningRate * db / n, "updated bias")});
}
