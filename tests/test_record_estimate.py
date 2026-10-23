from decimal import Decimal
import unittest

from src.record_estimate import calculate, positive_decimal


class RecordEstimateTests(unittest.TestCase):
    def test_hypothetical_costs_are_explicit_estimates(self):
        result = calculate(Decimal("0.0104"), Decimal("720"), Decimal("240"))
        self.assertEqual(result["before_usd"], "7.4880")
        self.assertEqual(result["after_usd"], "2.4960")
        self.assertEqual(result["difference_usd"], "4.9920")
        self.assertEqual(result["source"], "estimate")
        self.assertFalse(result["aws_actual"])

    def test_non_finite_and_negative_values_are_rejected(self):
        for value in ("NaN", "Infinity", "-1"):
            with self.assertRaises(Exception):
                positive_decimal(value)

    def test_database_precision_is_preserved(self):
        with self.assertRaises(ValueError):
            calculate(Decimal("0.1234567"), Decimal("1"), Decimal("0"))


if __name__ == "__main__":
    unittest.main()
