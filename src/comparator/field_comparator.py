from __future__ import annotations

from decimal import Decimal
from typing import Final, Literal

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
    validate_canonical,
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


def canonical_equal(field: FieldName, si_val: Canonical, bl_val: Canonical) -> bool:
    """Evaluate exact deterministic equality between two canonical values (DEC-01).

    Guards:
    - Text fields: exact string equality (no fuzzy matching, no suffix stripping, no port aliases).
    - container_count: exact integer equality (no floats, no booleans).
    - gross_weight_kg: exact Decimal mathematical equality (canonical Decimal only; no string conversion,
      no floats, no undocumented tolerance). T04 performs equality, NOT coercion.
    """
    validate_canonical(field, si_val)
    validate_canonical(field, bl_val)

    if field == "container_count":
        return si_val == bl_val
    elif field == "gross_weight_kg":
        require(
            isinstance(si_val, Decimal) and not isinstance(si_val, bool) and si_val.is_finite(),
            "gross_weight_kg canonical value must be a finite Decimal, not string or float",
        )
        require(
            isinstance(bl_val, Decimal) and not isinstance(bl_val, bool) and bl_val.is_finite(),
            "gross_weight_kg canonical value must be a finite Decimal, not string or float",
        )
        return si_val == bl_val
    else:
        return si_val == bl_val


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


def _validate_input_fields(
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


def compare_seven_fields(
    si: DocumentExtraction | dict[FieldName, ExtractedField] | dict[FieldName, Canonical],
    bl: DocumentExtraction | dict[FieldName, ExtractedField] | dict[FieldName, Canonical],
    rule_version: str = DEFAULT_RULE_VERSION,
) -> ComparatorResult:
    """Deterministically compare exactly the seven mandatory fields between SI and BL.

    Strict Architectural Invariants:
    1. Compares exactly the 7 mandatory fields (no eighth field). Direct dictionary inputs
       must have exactly the 7 approved FIELD_NAMES (missing or extra keys rejected).
    2. Pure deterministic software execution: zero LLM calls.
    3. Emits 'No mismatch detected' ONLY when all 7 fields are reliable, compared, and match.
    4. When any field is unresolved (missing, uncertain, conflicting, unreadable):
       - mismatch_detected is strictly None (DC-03)
       - outcome is strictly None
       - result_summary is NEVER 'No mismatch detected' (REG-010)
       - partial_result preserves all reliable comparisons and known mismatches (REG-009, DEC-AI-P04)
    """
    require(bool(rule_version and rule_version.strip()), "rule_version must be non-empty")
    si_fields = _validate_input_fields(si, "SI")
    bl_fields = _validate_input_fields(bl, "BL")

    comparisons: list[FieldComparison] = []
    discrepancies: list[Discrepancy] = []
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
            fc = compare_canonical_field(field, si_val, bl_val, rule_version=rule_version)
            comparisons.append(fc)
            if fc.outcome == "MISMATCH":
                discrepancies.append(Discrepancy(field=field, si_value=si_val, bl_value=bl_val))
        else:
            unresolved_fields.append(field)

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

    return ComparatorResult(
        partial_result=partial_result,
        discrepancies=discrepancies,
        mismatch_detected=mismatch_detected,
        outcome=outcome,
        result_summary=result_summary,
    )


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
