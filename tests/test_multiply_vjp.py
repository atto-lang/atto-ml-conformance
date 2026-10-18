"""Reference-only broadcast multiply VJP verification, including finite differences."""
import math
import random
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from tensor_shape_oracle import (
    broadcast_multiply, multiply_operand_gradient, ShapeError,
)


class MultiplyVJPTests(unittest.TestCase):
    def test_known_two_axis_broadcast(self):
        left_shape, right_shape = [2, 1], [1, 3]
        left, right = [2., 3.], [4., 5., 6.]
        shape, product = broadcast_multiply(left_shape, left, right_shape, right)
        self.assertEqual(shape, [2, 3])
        self.assertEqual(product, [8., 10., 12., 12., 15., 18.])
        upstream = [1., 2., 3., 4., 5., 6.]
        self.assertEqual(
            multiply_operand_gradient(left_shape, left, right_shape, right, upstream, True),
            [32., 77.])
        self.assertEqual(
            multiply_operand_gradient(left_shape, left, right_shape, right, upstream, False),
            [14., 19., 24.])

    def test_scalar_and_empty_broadcast(self):
        self.assertEqual(broadcast_multiply([], [3.], [2], [4., 5.]),
                         ([2], [12., 15.]))
        self.assertEqual(multiply_operand_gradient([], [3.], [2], [4., 5.],
                                                    [1., 2.], True), [14.])
        self.assertEqual(multiply_operand_gradient([0, 3], [], [1, 3],
                                                    [1., 2., 3.], [], False),
                         [0., 0., 0.])

    def test_negative_malformed_shapes(self):
        with self.assertRaises(ShapeError):
            broadcast_multiply([2], [1.], [2], [3., 4.])
        with self.assertRaises(ShapeError):
            multiply_operand_gradient([2], [1.], [2], [3., 4.], [1., 1.], True)
        with self.assertRaises(ShapeError):
            multiply_operand_gradient([2], [1., 2.], [2], [3., 4.], [1.], False)

    def test_seeded_both_operands_against_finite_differences(self):
        rng = random.Random(20261017)
        observations = 0
        epsilon = 1e-6
        for _ in range(120):
            rank = rng.randrange(0, 4)
            base = [rng.randrange(0, 4) for _ in range(rank)]
            left_shape = [rng.choice((d, 1)) for d in base]
            right_shape = [rng.choice((d, 1)) for d in base]
            left_shape = left_shape[rng.randrange(rank + 1):]
            right_shape = right_shape[rng.randrange(rank + 1):]
            left = [rng.uniform(-2., 2.) for _ in range(math.prod(left_shape))]
            right = [rng.uniform(-2., 2.) for _ in range(math.prod(right_shape))]
            result_shape, output = broadcast_multiply(left_shape, left, right_shape, right)
            upstream = [rng.uniform(-2., 2.) for _ in output]

            def objective(a, b):
                _, values = broadcast_multiply(left_shape, a, right_shape, b)
                return math.fsum(v * u for v, u in zip(values, upstream))

            for wrt_left in (True, False):
                grad = multiply_operand_gradient(left_shape, left, right_shape,
                                                 right, upstream, wrt_left)
                arg = left if wrt_left else right
                for i in range(len(arg)):
                    plus, minus = arg[:], arg[:]
                    plus[i] += epsilon
                    minus[i] -= epsilon
                    a = (objective(plus, right) - objective(minus, right)) if wrt_left else (
                        objective(left, plus) - objective(left, minus))
                    approx = a / (2 * epsilon)
                    self.assertAlmostEqual(grad[i], approx, delta=3e-7)
                    observations += 1
        self.assertGreater(observations, 100)


if __name__ == "__main__":
    unittest.main()
