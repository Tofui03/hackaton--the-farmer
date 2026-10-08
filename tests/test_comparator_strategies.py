from __future__ import annotations

from decimal import Decimal
import pytest

from src.comparator.strategies import (
    ContainerCountStrategy,
    GrossWeightStrategy,
    TextExactStrategy,
)


class TestTextExactStrategy:
    """Tests for TextExactStrategy covering normal equality and invariant validations."""

    def test_target_field(self) -> None:
        strategy_shipper = TextExactStrategy("shipper")
        assert strategy_shipper.target_field == "shipper"

        strategy_pod = TextExactStrategy("port_of_discharge")
        assert strategy_pod.target_field == "port_of_discharge"

    def test_invalid_field_initialization(self) -> None:
        with pytest.raises(ValueError, match="TextExactStrategy cannot handle field"):
            TextExactStrategy("container_count")  # type: ignore[arg-type]

    def test_are_equal_exact_match(self) -> None:
        strategy = TextExactStrategy("shipper")
        assert strategy.are_equal("COSCO SHIPPING CORP", "COSCO SHIPPING CORP") is True

    def test_are_equal_mismatch(self) -> None:
        strategy = TextExactStrategy("consignee")
        assert strategy.are_equal("ALIBABA LOGISTICS", "TENCENT LOGISTICS") is False

    def test_are_equal_case_sensitive(self) -> None:
        strategy = TextExactStrategy("notify_party")
        assert strategy.are_equal("SAME AS CONSIGNEE", "same as consignee") is False

    def test_are_equal_invalid_empty_or_whitespace(self) -> None:
        strategy = TextExactStrategy("port_of_loading")
        with pytest.raises(ValueError):
            strategy.are_equal("", "SHANGHAI")
        with pytest.raises(ValueError):
            strategy.are_equal("SHANGHAI", "   ")

    def test_are_equal_invalid_non_string(self) -> None:
        strategy = TextExactStrategy("port_of_discharge")
        with pytest.raises(ValueError):
            strategy.are_equal(12345, "ROTTERDAM")  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            strategy.are_equal("ROTTERDAM", None)  # type: ignore[arg-type]


class TestContainerCountStrategy:
    """Tests for ContainerCountStrategy covering integer strict equality."""

    def test_target_field(self) -> None:
        strategy = ContainerCountStrategy()
        assert strategy.target_field == "container_count"

    def test_are_equal_exact_match(self) -> None:
        strategy = ContainerCountStrategy()
        assert strategy.are_equal(5, 5) is True

    def test_are_equal_mismatch(self) -> None:
        strategy = ContainerCountStrategy()
        assert strategy.are_equal(5, 6) is False

    def test_are_equal_invalid_boolean(self) -> None:
        strategy = ContainerCountStrategy()
        # In Python, bool is a subclass of int, but validate_canonical rejects bool
        with pytest.raises(ValueError):
            strategy.are_equal(True, 1)  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            strategy.are_equal(1, False)  # type: ignore[arg-type]

    def test_are_equal_invalid_float_or_str(self) -> None:
        strategy = ContainerCountStrategy()
        with pytest.raises(ValueError):
            strategy.are_equal(5.0, 5)  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            strategy.are_equal("5", 5)  # type: ignore[arg-type]


class TestGrossWeightStrategy:
    """Tests for GrossWeightStrategy covering finite Decimal strict equality."""

    def test_target_field(self) -> None:
        strategy = GrossWeightStrategy()
        assert strategy.target_field == "gross_weight_kg"

    def test_are_equal_exact_match(self) -> None:
        strategy = GrossWeightStrategy()
        assert strategy.are_equal(Decimal("25000.50"), Decimal("25000.50")) is True
        # Decimal mathematical equality
        assert strategy.are_equal(Decimal("25000.5"), Decimal("25000.50")) is True

    def test_are_equal_mismatch(self) -> None:
        strategy = GrossWeightStrategy()
        assert strategy.are_equal(Decimal("25000.50"), Decimal("25001.00")) is False

    def test_are_equal_invalid_float(self) -> None:
        strategy = GrossWeightStrategy()
        with pytest.raises(ValueError):
            strategy.are_equal(25000.50, Decimal("25000.50"))  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            strategy.are_equal(Decimal("25000.50"), 25000.50)  # type: ignore[arg-type]

    def test_are_equal_invalid_string(self) -> None:
        strategy = GrossWeightStrategy()
        # validate_canonical allows string if formatted properly, but GrossWeightStrategy requires finite Decimal
        with pytest.raises(ValueError, match="finite Decimal"):
            strategy.are_equal("25000.50", Decimal("25000.50"))  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="finite Decimal"):
            strategy.are_equal(Decimal("25000.50"), "25000.50")  # type: ignore[arg-type]

    def test_are_equal_invalid_boolean(self) -> None:
        strategy = GrossWeightStrategy()
        with pytest.raises(ValueError):
            strategy.are_equal(True, Decimal("1.0"))  # type: ignore[arg-type]

    def test_are_equal_invalid_infinity_or_nan(self) -> None:
        strategy = GrossWeightStrategy()
        with pytest.raises(ValueError):
            strategy.are_equal(Decimal("Infinity"), Decimal("25000.00"))
        with pytest.raises(ValueError):
            strategy.are_equal(Decimal("NaN"), Decimal("25000.00"))
        with pytest.raises(ValueError):
            strategy.are_equal(Decimal("25000.00"), Decimal("-Infinity"))
