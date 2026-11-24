import unittest
from reference.numeric_oracle import NumericComparisonError, compare_vectors, require_guest_evidence


class NumericOracleTest(unittest.TestCase):
    def test_absolute_relative_and_exact(self):
        self.assertTrue(compare_vectors([1.0, 2.0], [1.0, 2.0])["passed"])
        self.assertTrue(compare_vectors([1000.0], [1000.1], rtol=0.001)["passed"])
        self.assertTrue(compare_vectors([0.0], [0.01], atol=0.02)["passed"])
        self.assertEqual(compare_vectors([0.0, 1.0], [0.0, 1.1])["failed_indices"], [1])

    def test_reject_nonfinite_and_invalid(self):
        for values in [[float("nan")], [float("inf")], [True], ["1.0"]]:
            with self.assertRaises(NumericComparisonError):
                compare_vectors([1], values)
        for kwargs in [{"atol": -1}, {"rtol": float("inf")},
                       {"atol": True}, {"max_elements": True}]:
            with self.assertRaises(NumericComparisonError):
                compare_vectors([1], [1], **kwargs)
        with self.assertRaises(NumericComparisonError):
            compare_vectors([1], [1, 2])

    def test_reject_ints_outside_finite_float_range(self):
        huge = 10 ** 1000
        for expected, observed, kwargs in [
            ([huge], [1], {}),
            ([1], [huge], {}),
            ([1], [1], {"atol": huge}),
            ([1], [1], {"rtol": huge}),
        ]:
            with self.subTest(kwargs=kwargs), self.assertRaises(NumericComparisonError):
                compare_vectors(expected, observed, **kwargs)

    def test_guest_evidence_fails_closed(self):
        meta = {"backend": "rs", "source_sha": "a" * 40,
                "execution": "guest", "evidence_sha256": "b" * 64}
        self.assertTrue(require_guest_evidence(meta))
        with self.assertRaises(NumericComparisonError):
            require_guest_evidence(dict(meta, execution="host"))


if __name__ == "__main__":
    unittest.main()
