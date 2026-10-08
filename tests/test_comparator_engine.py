from __future__ import annotations

from decimal import Decimal
import pytest

from src.comparator.engine import DeterministicComparisonEngine
from src.comparator.strategies.implementations import (
    ContainerCountStrategy,
    GrossWeightStrategy,
    TextExactStrategy,
)
from src.comparator.strategies.registry import ComparisonStrategyRegistry
from src.models.comparison import ComparisonOutcome
from src.models.extraction import Canonical, FieldCandidate, FieldName, NormalizedField, ExtractedField


def make_valid_canonical_dict() -> dict[FieldName, Canonical]:
    return {
        "shipper": "OCEAN NETWORK EXPRESS PTE LTD",
        "consignee": "GLOBAL IMPORTS CORP",
        "notify_party": "SAME AS CONSIGNEE",
        "port_of_loading": "SINGAPORE",
        "port_of_discharge": "ROTTERDAM",
        "container_count": 4,
        "gross_weight_kg": Decimal("18500.00"),
    }


def make_reliable_field(field: FieldName, val: Canonical) -> ExtractedField:
    candidate = FieldCandidate(
        raw_value=str(val),
        source_unit=None,
        evidence_ids=["ev_1"],
    )
    return ExtractedField(
        field=field,
        reliability="RELIABLE",
        candidates=[candidate],
        selected_candidate=0,
        normalized=NormalizedField(
            field=field,
            state="VALID",
            value=val,
            rule_version="norm-v1.0",
        ),
        explanation=f"Reliably extracted {field}",
    )


class TestDeterministicComparisonEngine:
    """Unit tests for DeterministicComparisonEngine domain service."""

    def test_all_seven_fields_match(self) -> None:
        engine = DeterministicComparisonEngine()
        si = make_valid_canonical_dict()
        bl = dict(si)

        result = engine.compare(si, bl)

        assert result.is_complete_match is True
        assert result.mismatch_detected is False
        assert result.outcome == ComparisonOutcome.MATCH
        assert result.result_summary == "No mismatch detected"
        assert len(result.discrepancies) == 0
        assert len(result.comparisons) == 7
        assert len(result.unresolved_fields) == 0

    def test_deterministic_mismatch_detected(self) -> None:
        engine = DeterministicComparisonEngine()
        si = make_valid_canonical_dict()
        bl = dict(si)
        bl["container_count"] = 5
        bl["port_of_discharge"] = "HAMBURG"

        result = engine.compare(si, bl)

        assert result.is_complete_match is False
        assert result.mismatch_detected is True
        assert result.outcome == ComparisonOutcome.MISMATCH
        assert "Mismatches detected" in result.result_summary
        assert "container_count" in result.result_summary
        assert "port_of_discharge" in result.result_summary
        assert len(result.discrepancies) == 2
        diff_fields = {d.field for d in result.discrepancies}
        assert diff_fields == {"container_count", "port_of_discharge"}

    def test_unresolved_field_scenario(self) -> None:
        engine = DeterministicComparisonEngine()
        si_fields: dict[FieldName, ExtractedField] = {
            f: make_reliable_field(f, v) for f, v in make_valid_canonical_dict().items()
        }
        bl_fields: dict[FieldName, ExtractedField] = {
            f: make_reliable_field(f, v) for f, v in make_valid_canonical_dict().items()
        }

        # Make shipper unreliable on BL side
        bl_fields["shipper"].reliability = "UNRELIABLE"

        result = engine.compare(si_fields, bl_fields)

        assert result.is_complete_match is False
        assert result.mismatch_detected is None
        assert result.outcome is None
        assert "shipper" in result.unresolved_fields
        assert "Review required: 1 field(s) unresolved (shipper)" in result.result_summary
        assert len(result.comparisons) == 6

    def test_unresolved_with_concurrent_mismatch(self) -> None:
        engine = DeterministicComparisonEngine()
        si_fields: dict[FieldName, ExtractedField] = {
            f: make_reliable_field(f, v) for f, v in make_valid_canonical_dict().items()
        }
        bl_fields: dict[FieldName, ExtractedField] = {
            f: make_reliable_field(f, v) for f, v in make_valid_canonical_dict().items()
        }

        # Shipper unresolved + container_count mismatch
        bl_fields["shipper"].reliability = "UNRELIABLE"
        bl_fields["container_count"] = make_reliable_field("container_count", 99)

        result = engine.compare(si_fields, bl_fields)

        assert result.mismatch_detected is None
        assert result.outcome is None
        assert "Review required" in result.result_summary
        assert "mismatches detected in: container_count" in result.result_summary
        assert len(result.discrepancies) == 1

    def test_invalid_input_missing_fields_raises_value_error(self) -> None:
        engine = DeterministicComparisonEngine()
        si = make_valid_canonical_dict()
        del si["shipper"]
        bl = make_valid_canonical_dict()

        with pytest.raises(ValueError, match="SI input must contain exactly the 7 mandatory fields"):
            engine.compare(si, bl)

    def test_invalid_input_extra_fields_raises_value_error(self) -> None:
        engine = DeterministicComparisonEngine()
        si = make_valid_canonical_dict()
        si["extra_field"] = "foo"  # type: ignore[assignment]
        bl = make_valid_canonical_dict()

        with pytest.raises(ValueError, match="SI input must contain exactly the 7 mandatory fields"):
            engine.compare(si, bl)

    def test_custom_registry_dependency_injection(self) -> None:
        registry = ComparisonStrategyRegistry()
        engine = DeterministicComparisonEngine(registry=registry)
        assert engine.registry is registry
