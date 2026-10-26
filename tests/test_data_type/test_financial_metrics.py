import unittest

import numpy as np

from smrti_quant_alerts.data_type.financial_metrics import FinancialMetricsData, FinancialDataType


class TestFinancialMetricsData(unittest.TestCase):
    def test_init(self) -> None:
        self.assertEqual(FinancialMetricsData(), 0)
        self.assertEqual(FinancialMetricsData(np.nan), 0)
        self.assertEqual(FinancialMetricsData(np.inf), 0)
        self.assertEqual(FinancialMetricsData(FinancialMetricsData(5)), 5)

        self.assertEqual(FinancialMetricsData("3.5", FinancialDataType.STRING_FLOAT), 3.5)
        self.assertEqual(FinancialMetricsData(12.5, FinancialDataType.PERCENTAGE, True), 0.125)
        self.assertEqual(FinancialMetricsData("12.5", FinancialDataType.STRING_PERCENTAGE, True), 0.125)
        self.assertEqual(FinancialMetricsData("12.5%", FinancialDataType.STRING_PERCENTAGE_WITH_SIGN, True), 0.125)
        self.assertEqual(FinancialMetricsData("12.5", FinancialDataType.STRING_PERCENTAGE), 0)

    def test_properties(self) -> None:
        data = FinancialMetricsData(0.125, FinancialDataType.FLOAT, True)
        self.assertEqual(data.float_data, 0.125)
        self.assertEqual(data.percentage_data, 12.5)
        self.assertEqual(data.string_float_data, "0.125")
        self.assertEqual(data.string_percentage_data, "12.5%")
        self.assertEqual(str(data), "12.5%")
        self.assertEqual(repr(data), "12.5%")

        data.update_data(0.25, FinancialDataType.FLOAT)
        self.assertEqual(data.percentage_data, 25)

        non_percentage = FinancialMetricsData(1.5)
        self.assertEqual(non_percentage.percentage_data, 0)
        self.assertEqual(non_percentage.string_percentage_data, "")
        self.assertEqual(str(non_percentage), "1.5")

    def test_comparisons(self) -> None:
        smaller = FinancialMetricsData(2)
        larger = FinancialMetricsData(3)

        self.assertTrue(smaller < larger)
        self.assertTrue(smaller < 3)
        self.assertTrue(smaller <= larger)
        self.assertTrue(smaller <= 2)
        self.assertTrue(larger > smaller)
        self.assertTrue(larger > 2)
        self.assertTrue(larger >= smaller)
        self.assertTrue(larger >= 3)
        self.assertTrue(smaller == 2)
        self.assertTrue(smaller != larger)
        self.assertTrue(smaller != 3)

    def test_arithmetic(self) -> None:
        smaller = FinancialMetricsData(2)
        larger = FinancialMetricsData(3)

        self.assertEqual(smaller + larger, 5)
        self.assertEqual(smaller + 3, 5)
        self.assertEqual(3 + smaller, 5)
        self.assertEqual(larger - smaller, 1)
        self.assertEqual(larger - 1, 2)
        self.assertEqual(smaller * larger, 6)
        self.assertEqual(smaller * 2, 4)
        self.assertEqual(larger / smaller, 1.5)
        self.assertEqual(larger / 2, 1.5)
        self.assertEqual(larger / FinancialMetricsData(0), 0)
        self.assertEqual(larger / 0, 0)

        percentage = FinancialMetricsData(0.5, FinancialDataType.FLOAT, True)
        self.assertEqual((percentage + 0.5).percentage_data, 100)
