"""Independent coordinate-based tensor tests; no Oreslang compiler is executed."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from tensor_shape_oracle import broadcast_add, sum_to_shape, ShapeError


class TensorShapeOracleTests(unittest.TestCase):
    def test_right_aligned_broadcast(self):
        shape, result = broadcast_add([2, 1], [10., 20.], [1, 3], [1., 2., 3.])
        self.assertEqual(shape, [2, 3])
        self.assertEqual(result, [11., 12., 13., 21., 22., 23.])

    def test_scalar(self):
        self.assertEqual(broadcast_add([], [5.], [3], [1., 2., 3.]),
                         ([3], [6., 7., 8.]))

    def test_zero_extent(self):
        self.assertEqual(broadcast_add([0, 3], [], [1, 3], [1., 2., 3.]),
                         ([0, 3], []))
        self.assertEqual(sum_to_shape([0, 3], [], [1, 3]), [0., 0., 0.])

    def test_unbroadcast(self):
        source = [1., 2., 3., 4., 5., 6.]
        self.assertEqual(sum_to_shape([2, 3], source, [1, 3]), [5., 7., 9.])
        self.assertEqual(sum_to_shape([2, 3], source, []), [21.])

    def test_mismatched(self):
        with self.assertRaises(ShapeError):
            broadcast_add([2], [1., 2.], [3], [1., 2., 3.])
        with self.assertRaises(ShapeError):
            sum_to_shape([2, 3], [1.] * 6, [3, 1])

    def test_shape_storage_mismatch(self):
        with self.assertRaises(ShapeError):
            broadcast_add([2, 2], [1.], [], [5.])
        with self.assertRaises(ShapeError):
            sum_to_shape([2, 2], [1.], [2, 2])


if __name__ == "__main__":
    unittest.main()
