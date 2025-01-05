from __future__ import annotations
from enum import Enum, StrEnum
from typing import Union


class FinancialMetricType(StrEnum):
    REVENUE = "revenue"
    MARKET_CAP = "market_cap"
    NET_INCOME = "net_income"
    GROSS_MARGIN = "gross_margin"
    OPERATING_MARGIN = "operating_margin"
    FREE_CASH_FLOW = "free_cash_flow"
    FREE_CASH_FLOW_MARGIN = "free_cash_flow_margin"
    REVENUE_1Y_CAGR = "revenue_1y_cagr"
    REVENUE_3Y_CAGR = "revenue_3y_cagr"
    REVENUE_5Y_CAGR = "revenue_5y_cagr"
    OUTSTANDING_SHARES = "outstanding_shares"
    ENTERPRISE_VALUE = "enterprise_value"
    GROWTH_SCORE = "growth_score"
    REVENUE_YOY_GROWTH = "revenue_yoy_growth"
    REVENUE_YOY_GROWTH_LATEST = "revenue_yoy_growth_latest"
    REVENUE_YOY_GROWTH_SECOND_LATEST = "revenue_yoy_growth_second_latest"
    REVENUE_YOY_GROWTH_SUM = "revenue_yoy_growth_sum"
    FREE_CASH_FLOW_MARGIN_LATEST = "free_cash_flow_margin_latest"
    FREE_CASH_FLOW_MARGIN_SECOND_LATEST = "free_cash_flow_margin_second_latest"
    FREE_CASH_FLOW_MARGIN_AVG = "free_cash_flow_margin_avg"
    VALUATION_SCORE = "valuation_score"
    GROSS_PROFIT = "gross_profit"
    OPERATING_INCOME = "operating_income"


class FinancialDataType(Enum):
    FLOAT = 1
    PERCENTAGE = 2
    STRING_FLOAT = 3
    STRING_PERCENTAGE = 4
    STRING_PERCENTAGE_WITH_SIGN = 5


class FinancialMetricsData:
    def __init__(self, data: Union[float, str, FinancialMetricsData] = 0,
                 data_type: FinancialDataType = FinancialDataType.FLOAT,
                 has_percentage: bool = False) -> None:
        if isinstance(data, FinancialMetricsData):
            data = data.float_data
        self._has_percentage = has_percentage
        self._float_data = self._convert_to_float(data, data_type)

    def _convert_to_float(self, data: Union[float, str], data_type: FinancialDataType) -> float:
        if data_type == FinancialDataType.FLOAT:
            return data
        if data_type == FinancialDataType.STRING_FLOAT:
            return float(data)
        if not self._has_percentage:
            return 0.0
        if data_type == FinancialDataType.PERCENTAGE or data_type == FinancialDataType.STRING_PERCENTAGE:
            return float(data) / 100
        if data_type == FinancialDataType.STRING_PERCENTAGE_WITH_SIGN:
            return float(data.strip("%")) / 100
        return 0.0

    @property
    def float_data(self) -> float:
        return round(self._float_data, 6)

    @property
    def percentage_data(self) -> float:
        if not self._has_percentage:
            return 0.0
        return round(self._float_data * 100, 4)

    @property
    def string_float_data(self) -> str:
        return str(round(self._float_data, 6))

    @property
    def string_percentage_data(self) -> str:
        if not self._has_percentage:
            return ""
        return f"{round(self._float_data * 100, 4)}%"

    def update_data(self, data: Union[float, str], data_type: FinancialDataType) -> None:
        self._float_data = self._convert_to_float(data, data_type)

    def __str__(self) -> str:
        if self._has_percentage:
            return self.string_percentage_data
        return self.string_float_data

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other: Union[FinancialMetricsData, float]) -> bool:
        if isinstance(other, FinancialMetricsData):
            return self.float_data == other.float_data
        return self.float_data == other

    def __ne__(self, other: Union[FinancialMetricsData, float]) -> bool:
        return not self.__eq__(other)

    def __lt__(self, other: Union[FinancialMetricsData, float]) -> bool:
        if isinstance(other, FinancialMetricsData):
            return self.float_data < other.float_data
        return self.float_data < other

    def __le__(self, other: Union[FinancialMetricsData, float]) -> bool:
        return self.__lt__(other) or self.__eq__(other)

    def __gt__(self, other: Union[FinancialMetricsData, float]) -> bool:
        if isinstance(other, FinancialMetricsData):
            return self.float_data > other.float_data
        return self.float_data > other

    def __ge__(self, other: Union[FinancialMetricsData, float]) -> bool:
        return self.__gt__(other) or self.__eq__(other)

    def __add__(self, other: Union[FinancialMetricsData, float]) -> FinancialMetricsData:
        if isinstance(other, FinancialMetricsData):
            return FinancialMetricsData(self.float_data + other.float_data,
                                        FinancialDataType.FLOAT, self._has_percentage)
        return FinancialMetricsData(self.float_data + other, FinancialDataType.FLOAT, self._has_percentage)

    def __radd__(self, other: Union[FinancialMetricsData, float]) -> FinancialMetricsData:
        return self.__add__(other)

    def __sub__(self, other: Union[FinancialMetricsData, float]) -> FinancialMetricsData:
        if isinstance(other, FinancialMetricsData):
            return FinancialMetricsData(self.float_data - other.float_data,
                                        FinancialDataType.FLOAT, self._has_percentage)
        return FinancialMetricsData(self.float_data - other, FinancialDataType.FLOAT, self._has_percentage)

    def __mul__(self, other: Union[FinancialMetricsData, float]) -> FinancialMetricsData:
        if isinstance(other, FinancialMetricsData):
            return FinancialMetricsData(self.float_data * other.float_data,
                                        FinancialDataType.FLOAT, self._has_percentage)
        return FinancialMetricsData(self.float_data * other, FinancialDataType.FLOAT, self._has_percentage)

    def __truediv__(self, other: Union[FinancialMetricsData, float]) -> FinancialMetricsData:
        if isinstance(other, FinancialMetricsData):
            if other.float_data == 0:
                return FinancialMetricsData(0, FinancialDataType.FLOAT, self._has_percentage)
            return FinancialMetricsData(self.float_data / other.float_data,
                                        FinancialDataType.FLOAT, self._has_percentage)
        if other == 0:
            return FinancialMetricsData(0, FinancialDataType.FLOAT, self._has_percentage)
        return FinancialMetricsData(self.float_data / other, FinancialDataType.FLOAT, self._has_percentage)
