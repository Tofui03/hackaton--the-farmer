from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal
import pytest

from src.domain.values import ContainerCount, GrossWeight, ValueObject


class TestValueObjectBase:
    """Tests for base ValueObject characteristics."""

    def test_structural_equality(self) -> None:
        c1 = ContainerCount(5)
        c2 = ContainerCount(5)
        assert c1 == c2
        assert hash(c1) == hash(c2)

    def test_immutability(self) -> None:
        c = ContainerCount(5)
        with pytest.raises(FrozenInstanceError):
            c.value = 10  # type: ignore[misc]

        w = GrossWeight(Decimal("25000"))
        with pytest.raises(FrozenInstanceError):
            w.value = Decimal("30000")  # type: ignore[misc]


class TestContainerCount:
    """Tests for ContainerCount Value Object."""

    def test_valid_instantiation(self) -> None:
        cc = ContainerCount(2)
        assert cc.value == 2
        assert cc.to_canonical() == 2

    def test_invalid_values(self) -> None:
        with pytest.raises(ValueError, match="greater than 0"):
            ContainerCount(0)
        with pytest.raises(ValueError, match="greater than 0"):
            ContainerCount(-1)
        with pytest.raises(ValueError, match="must be an integer"):
            ContainerCount(True)  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="must be an integer"):
            ContainerCount(2.5)  # type: ignore[arg-type]

    def test_from_input_valid(self) -> None:
        assert ContainerCount.from_input(2).to_canonical() == 2
        assert ContainerCount.from_input("5").to_canonical() == 5
        assert ContainerCount.from_input("  12  ").to_canonical() == 12

    def test_from_input_invalid(self) -> None:
        with pytest.raises(ValueError):
            ContainerCount.from_input(None)
        with pytest.raises(ValueError):
            ContainerCount.from_input(True)
        with pytest.raises(ValueError):
            ContainerCount.from_input(2.0)
        with pytest.raises(ValueError):
            ContainerCount.from_input("")
        with pytest.raises(ValueError):
            ContainerCount.from_input("two")
        with pytest.raises(ValueError):
            ContainerCount.from_input("2 containers")
        with pytest.raises(ValueError):
            ContainerCount.from_input("-5")


class TestGrossWeight:
    """Tests for GrossWeight Value Object."""

    def test_valid_instantiation(self) -> None:
        gw = GrossWeight(Decimal("22000.50"))
        assert gw.value == Decimal("22000.50")
        assert gw.unit == "KG"
        assert gw.to_canonical() == Decimal("22000.50")

    def test_invalid_instantiation(self) -> None:
        with pytest.raises(ValueError, match="greater than 0"):
            GrossWeight(Decimal("0"))
        with pytest.raises(ValueError, match="greater than 0"):
            GrossWeight(Decimal("-100"))
        with pytest.raises(ValueError, match="cannot be a boolean"):
            GrossWeight(True)  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="must be a Decimal"):
            GrossWeight(22000.5)  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="finite Decimal"):
            GrossWeight(Decimal("Infinity"))

    def test_from_input_conversions(self) -> None:
        # Exact decimal / int
        assert GrossWeight.from_input(Decimal("22000")).to_canonical() == Decimal("22000")
        assert GrossWeight.from_input(22000).to_canonical() == Decimal("22000")

        # Plain numeric string
        assert GrossWeight.from_input("22000").to_canonical() == Decimal("22000")
        assert GrossWeight.from_input("25,432.50").to_canonical() == Decimal("25432.50")

        # KG variants
        assert GrossWeight.from_input("22000 kg").to_canonical() == Decimal("22000")
        assert GrossWeight.from_input("22000.5 KGS").to_canonical() == Decimal("22000.5")
        assert GrossWeight.from_input("22000 KILOGRAMS").to_canonical() == Decimal("22000")

        # MT variants (factor 1000)
        assert GrossWeight.from_input("22 MT").to_canonical() == Decimal("22000")
        assert GrossWeight.from_input("22.5 METRIC TONS").to_canonical() == Decimal("22500")
        assert GrossWeight.from_input("22 M/T").to_canonical() == Decimal("22000")
        assert GrossWeight.from_input("15 T").to_canonical() == Decimal("15000")

        # LBS variants (factor 0.45359237)
        lbs_res = GrossWeight.from_input("10000 LBS").to_canonical()
        assert lbs_res == Decimal("10000") * Decimal("0.45359237")
        lb_res = GrossWeight.from_input("50000 LB").to_canonical()
        assert lb_res == Decimal("50000") * Decimal("0.45359237")

    def test_from_input_guards_and_rejections(self) -> None:
        # None & empty
        with pytest.raises(ValueError):
            GrossWeight.from_input(None)
        with pytest.raises(ValueError):
            GrossWeight.from_input("")
        with pytest.raises(ValueError):
            GrossWeight.from_input("   ")

        # Binary float rejection (IEEE precision preservation)
        with pytest.raises(ValueError, match="float is rejected"):
            GrossWeight.from_input(22500.50)

        # Boolean rejection
        with pytest.raises(ValueError):
            GrossWeight.from_input(False)

        # Ambiguous keywords rejection
        with pytest.raises(ValueError, match="Ambiguous"):
            GrossWeight.from_input("APPROX 22 MT")
        with pytest.raises(ValueError, match="Ambiguous"):
            GrossWeight.from_input("TBD")
        with pytest.raises(ValueError, match="Ambiguous"):
            GrossWeight.from_input("ESTIMATED 25000 KG")

        # Range / alternation rejection
        with pytest.raises(ValueError, match="Range or alternation"):
            GrossWeight.from_input("22000 TO 23000 KG")
        with pytest.raises(ValueError, match="Range or alternation"):
            GrossWeight.from_input("22000 OR 23000 KG")
