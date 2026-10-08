from __future__ import annotations

from typing import Final, Literal

from src.comparator.strategies.base import FieldComparisonStrategy
from src.comparator.strategies.registry import (
    DEFAULT_STRATEGY_REGISTRY,
    ComparisonStrategyRegistry,
)
from src.models.base import Contract, Text, require
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


def is_field_reliable_and_valid(extracted_field: ExtractedField | None) -> bool:
    """Check if an extracted field is reliable and carries a valid normalized value."""
    if extracted_field is None:
        return False
    if extracted_field.reliability != "RELIABLE":
        return False
    if extracted_field.normalized is None:
        return False
    if extracted_field.normalized.state != "VALID":
        return False
    if extracted_field.normalized.value is None:
        return False
    return True


class ComparatorResult(Contract):
    """Result of deterministic seven-field comparison between SI and Draft BL."""

    partial_result: PartialResult
    discrepancies: list[Discrepancy]
    mismatch_detected: bool | None
    outcome: ComparisonOutcome | None
    result_summary: Text

    @property
    def comparisons(self) -> list[FieldComparison]:
        return self.partial_result.comparisons

    @property
    def unresolved_fields(self) -> list[FieldName]:
        return self.partial_result.unresolved_fields

    @property
    def is_complete_match(self) -> bool:
        return self.outcome == ComparisonOutcome.MATCH and self.mismatch_detected is False


class DeterministicComparisonEngine:
    """Domain service for deterministic seven-field comparison between SI and BL."""

    def __init__(self, registry: ComparisonStrategyRegistry | None = None) -> None:
        self.registry: ComparisonStrategyRegistry = registry or DEFAULT_STRATEGY_REGISTRY

    def _validate_input_fields(
        self,
        data: DocumentExtraction | dict[FieldName, ExtractedField] | dict[FieldName, Canonical],
        side_name: str,
    ) -> dict[FieldName, ExtractedField | Canonical | None]:
        """Validate that direct dictionary inputs contain exactly the seven approved FIELD_NAMES."""
        if isinstance(data, DocumentExtraction):
            return data.fields
        if isinstance(data, dict):
            keys_set = set(data.keys())
            expected_set = set(FIELD_NAMES)
            if keys_set != expected_set:
                missing = sorted(expected_set - keys_set)
                extra = sorted(keys_set - expected_set)
                err_parts: list[str] = []
                if missing:
                    err_parts.append(f"missing mandatory field(s): {missing}")
                if extra:
                    err_parts.append(f"extra/unknown field(s): {extra}")
                raise ValueError(
                    f"{side_name} input must contain exactly the 7 mandatory fields: {'; '.join(err_parts)}"
                )
            return data
        raise TypeError(f"{side_name} must be DocumentExtraction or dict, got {type(data).__name__}")

    def _extract_canonical_pairs(
        self,
        si_fields: dict[FieldName, ExtractedField | Canonical | None],
        bl_fields: dict[FieldName, ExtractedField | Canonical | None],
    ) -> tuple[
        dict[FieldName, tuple[Canonical, Canonical]],
        list[FieldName],
    ]:
        """Extract reliable canonical value pairs and detect unresolved fields."""
        resolved_pairs: dict[FieldName, tuple[Canonical, Canonical]] = {}
        unresolved_fields: list[FieldName] = []

        for field in FIELD_NAMES:
            si_entry = si_fields.get(field)
            bl_entry = bl_fields.get(field)

            si_val: Canonical | None = None
            if isinstance(si_entry, ExtractedField):
                if is_field_reliable_and_valid(si_entry):
                    assert si_entry.normalized is not None and si_entry.normalized.value is not None
                    si_val = si_entry.normalized.value
            elif si_entry is not None:
                si_val = si_entry

            bl_val: Canonical | None = None
            if isinstance(bl_entry, ExtractedField):
                if is_field_reliable_and_valid(bl_entry):
                    assert bl_entry.normalized is not None and bl_entry.normalized.value is not None
                    bl_val = bl_entry.normalized.value
            elif bl_entry is not None:
                bl_val = bl_entry

            if si_val is not None and bl_val is not None:
                resolved_pairs[field] = (si_val, bl_val)
            else:
                unresolved_fields.append(field)

        return resolved_pairs, unresolved_fields

    def _evaluate_field(
        self,
        field: FieldName,
        si_val: Canonical,
        bl_val: Canonical,
        rule_version: str,
    ) -> tuple[FieldComparison, Discrepancy | None]:
        """Evaluate equality using strategy registry and produce comparison record."""
        strategy: FieldComparisonStrategy = self.registry.get_strategy(field)
        is_equal = strategy.are_equal(si_val, bl_val)
        outcome: Literal["MATCH", "MISMATCH"] = "MATCH" if is_equal else "MISMATCH"

        fc = FieldComparison(
            field=field,
            si_value=si_val,
            bl_value=bl_val,
            outcome=outcome,
            rule_version=rule_version,
        )
        discrepancy = (
            Discrepancy(field=field, si_value=si_val, bl_value=bl_val)
            if outcome == "MISMATCH"
            else None
        )
        return fc, discrepancy

    def _arbitrate_outcome(
        self,
        comparisons: list[FieldComparison],
        discrepancies: list[Discrepancy],
        unresolved_fields: list[FieldName],
    ) -> tuple[PartialResult, list[Discrepancy], bool | None, ComparisonOutcome | None, Text]:
        """Arbitrate partial result, mismatch flag, outcome enum, and summary text."""
        partial_result = PartialResult(
            comparisons=comparisons,
            unresolved_fields=unresolved_fields,
        )

        if unresolved_fields:
            mismatch_detected: bool | None = None
            outcome: ComparisonOutcome | None = None
            unresolved_str = ", ".join(unresolved_fields)
            if discrepancies:
                disc_str = ", ".join(d.field for d in discrepancies)
                result_summary = (
                    f"Review required: {len(unresolved_fields)} field(s) unresolved ({unresolved_str}); "
                    f"mismatches detected in: {disc_str}"
                )
            else:
                result_summary = f"Review required: {len(unresolved_fields)} field(s) unresolved ({unresolved_str})"
        else:
            if discrepancies:
                mismatch_detected = True
                outcome = ComparisonOutcome.MISMATCH
                diff_fields = ", ".join(d.field for d in discrepancies)
                result_summary = f"Mismatches detected: {diff_fields}"
            else:
                mismatch_detected = False
                outcome = ComparisonOutcome.MATCH
                result_summary = "No mismatch detected"

        return partial_result, discrepancies, mismatch_detected, outcome, result_summary

    def compare(
        self,
        si: DocumentExtraction | dict[FieldName, ExtractedField] | dict[FieldName, Canonical],
        bl: DocumentExtraction | dict[FieldName, ExtractedField] | dict[FieldName, Canonical],
        rule_version: str = DEFAULT_RULE_VERSION,
    ) -> ComparatorResult:
        """Deterministically compare exactly the seven mandatory fields between SI and BL."""
        require(bool(rule_version and rule_version.strip()), "rule_version must be non-empty")
        si_fields = self._validate_input_fields(si, "SI")
        bl_fields = self._validate_input_fields(bl, "BL")

        resolved_pairs, unresolved_fields = self._extract_canonical_pairs(si_fields, bl_fields)

        comparisons: list[FieldComparison] = []
        discrepancies: list[Discrepancy] = []

        for field in FIELD_NAMES:
            if field in resolved_pairs:
                si_val, bl_val = resolved_pairs[field]
                fc, disc = self._evaluate_field(field, si_val, bl_val, rule_version=rule_version)
                comparisons.append(fc)
                if disc is not None:
                    discrepancies.append(disc)

        (
            partial_result,
            discrepancies,
            mismatch_detected,
            outcome,
            result_summary,
        ) = self._arbitrate_outcome(comparisons, discrepancies, unresolved_fields)

        return ComparatorResult(
            partial_result=partial_result,
            discrepancies=discrepancies,
            mismatch_detected=mismatch_detected,
            outcome=outcome,
            result_summary=result_summary,
        )
