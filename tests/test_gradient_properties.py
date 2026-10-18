"""Deterministic broadcast-gradient finite differences: reference-only."""
import math
import random
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from tensor_shape_oracle import broadcast_add, sum_to_shape


class BroadcastGradientProperties(unittest.TestCase):
    def test_sum_to_shape_matches_derivative_of_broadcast_add(self):
        rng = random.Random(20261018)
        h = 1e-6
        observations = 0
        for _ in range(160):
            rank = rng.randrange(0, 4)
            output_shape = [rng.randrange(0, 4) for _ in range(rank)]
            left_shape = [rng.choice((d, 1)) for d in output_shape]
            right_shape = [rng.choice((d, 1)) for d in output_shape]
            left_shape = left_shape[rng.randrange(0, rank+1):]
            right_shape = right_shape[rng.randrange(0, rank+1):]
            left = [rng.uniform(-2.0, 2.0) for _ in range(math.prod(left_shape))]
            right = [rng.uniform(-2.0, 2.0) for _ in range(math.prod(right_shape))]
            shape, values = broadcast_add(left_shape, left, right_shape, right)
            upstream = [rng.uniform(-2.0, 2.0) for _ in values]
            gradient = sum_to_shape(shape, upstream, left_shape)

            def objective(inputs):
                _, produced = broadcast_add(left_shape, inputs, right_shape, right)
                return math.fsum(p * w for p, w in zip(produced, upstream))

            for i in range(len(left)):
                plus, minus = left[:], left[:]
                plus[i] += h
                minus[i] -= h
                numerical = (objective(plus) - objective(minus)) / (2 * h)
                self.assertAlmostEqual(gradient[i], numerical, delta=2e-7)
                observations += 1
        self.assertGreater(observations, 100)


if __name__ == "__main__":
    unittest.main()
