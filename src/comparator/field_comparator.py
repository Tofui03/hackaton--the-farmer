from __future__ import annotations

from typing import Final, Literal

from src.comparator.engine import (
    ComparatorResult,
    DeterministicComparisonEngine,
    is_field_reliable_and_valid,
)
from src.comparator.strategies import DEFAULT_STRATEGY_REGISTRY
from src.models.base import Text, require
from src.models.comparison import (
    ComparisonOutcome,
    Discrepancy,
    FieldComparison,
    PartialResult,
)
from src.models.extraction import (
    FIELD_NAMES,
    Canonical,
    DocumentExtraction,
    ExtractedField,
    FieldName,
)

DEFAULT_RULE_VERSION: Final[str] = "norm-v1.0"
DEFAULT_COMPARATOR_ENGINE: Final[DeterministicComparisonEngine] = DeterministicComparisonEngine(
    DEFAULT_STRATEGY_REGISTRY
)


def canonical_equal(field: FieldName, si_val: Canonical, bl_val: Canonical) -> bool:
    """Evaluate exact deterministic equality between two canonical values (DEC-01).

    Refactored to delegate to domain FieldComparisonStrategy via registry.
    """
    strategy = DEFAULT_STRATEGY_REGISTRY.get_strategy(field)
    return strategy.are_equal(si_val, bl_val)


def compare_canonical_field(
    field: FieldName,
    si_val: Canonical,
    bl_val: Canonical,
    rule_version: str = DEFAULT_RULE_VERSION,
) -> FieldComparison:
    """Compare two canonical values for a single field and emit a FieldComparison."""
    require(bool(rule_version and rule_version.strip()), "rule_version must be non-empty")
    outcome: Literal["MATCH", "MISMATCH"] = (
        "MATCH" if canonical_equal(field, si_val, bl_val) else "MISMATCH"
    )
    return FieldComparison(
        field=field,
        si_value=si_val,
        bl_value=bl_val,
        outcome=outcome,
        rule_version=rule_version,
    )


def compare_extracted_fields(
    si_field: ExtractedField,
    bl_field: ExtractedField,
    rule_version: str = DEFAULT_RULE_VERSION,
) -> FieldComparison | None:
    """Compare two ExtractedFields if both pass the reliability gate, else None."""
    require(bool(rule_version and rule_version.strip()), "rule_version must be non-empty")
    if not is_field_reliable_and_valid(si_field) or not is_field_reliable_and_valid(bl_field):
        return None
    assert si_field.normalized is not None and si_field.normalized.value is not None
    assert bl_field.normalized is not None and bl_field.normalized.value is not None
    return compare_canonical_field(
        si_field.field,
        si_field.normalized.value,
        bl_field.normalized.value,
        rule_version=rule_version,
    )


def compare_seven_fields(
    si: DocumentExtraction | dict[FieldName, ExtractedField] | dict[FieldName, Canonical],
    bl: DocumentExtraction | dict[FieldName, ExtractedField] | dict[FieldName, Canonical],
    rule_version: str = DEFAULT_RULE_VERSION,
) -> ComparatorResult:
    """Deterministically compare exactly the seven mandatory fields between SI and BL."""
    return DEFAULT_COMPARATOR_ENGINE.compare(si, bl, rule_version=rule_version)


class FieldComparator:
    """Pure deterministic 7-field comparator engine (T04-01, T04-02)."""

    def __init__(self, rule_version: str = DEFAULT_RULE_VERSION) -> None:
        require(bool(rule_version and rule_version.strip()), "rule_version must be non-empty")
        self.rule_version = rule_version

    def compare_canonical_field(
        self,
        field: FieldName,
        si_val: Canonical,
        bl_val: Canonical,
    ) -> FieldComparison:
        return compare_canonical_field(field, si_val, bl_val, rule_version=self.rule_version)

    def compare(
        self,
        si: DocumentExtraction | dict[FieldName, ExtractedField] | dict[FieldName, Canonical],
        bl: DocumentExtraction | dict[FieldName, ExtractedField] | dict[FieldName, Canonical],
    ) -> ComparatorResult:
        return compare_seven_fields(si, bl, rule_version=self.rule_version)
