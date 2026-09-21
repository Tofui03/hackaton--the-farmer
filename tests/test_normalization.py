from __future__ import annotations

from decimal import Decimal
import pytest

import src.normalization
from src.models.extraction import NormalizedGrossWeight
from src.normalization import (
    RULE_VERSION,
    clean_punctuation,
    normalize_container_count,
    normalize_gross_weight_kg,
    normalize_text,
    normalize_unicode,
    normalize_whitespace_and_case,
    to_decimal_kg,
    to_normalized_gross_weight,
)


def test_ut_norm_001_unicode_normalization() -> None:
    """UT-NORM-001: Unicode Normalization (DEC-P06A) fullwidth to NFKC standard."""
    raw = "ＳＨＡＮＧＨＡＩ"
    normalized = normalize_unicode(raw)
    assert normalized == "SHANGHAI"

    # End-to-end field normalization check
    field_norm = normalize_text("port_of_loading", raw)
    assert field_norm.state == "VALID"
    assert field_norm.value == "SHANGHAI"
    assert field_norm.rule_version == RULE_VERSION


def test_ut_norm_002_case_folding_and_spacing() -> None:
    """UT-NORM-002: Case-Folding & Spacing (DEC-P06A) collapsed whitespace and uppercase."""
    raw = "  Acme   Industrial   Corp.  "
    normalized = normalize_whitespace_and_case(raw)
    assert normalized == "ACME INDUSTRIAL CORP."


def test_ut_norm_003_punctuation_cleanup() -> None:
    """UT-NORM-003: Punctuation Cleanup (DEC-P06A) trailing punctuation trimmed."""
    raw = "ROTTERDAM, NETHERLANDS."
    normalized = clean_punctuation(raw)
    assert normalized == "ROTTERDAM, NETHERLANDS"

    # End-to-end field normalization check
    field_norm = normalize_text("port_of_discharge", raw)
    assert field_norm.state == "VALID"
    assert field_norm.value == "ROTTERDAM, NETHERLANDS"
    assert field_norm.rule_version == RULE_VERSION

    # Quotes standardization (straight ASCII quotes)
    curly_double = clean_punctuation("“CONTAINERIZED CARGO”")
    assert curly_double == '"CONTAINERIZED CARGO"'

    curly_single = clean_punctuation("‘SPECIAL HANDLING’")
    assert curly_single == "'SPECIAL HANDLING'"


def test_ut_norm_004_metric_ton_conversion() -> None:
    """UT-NORM-004: Metric Ton Conversion (DEC-P06B) MT * 1000 = KG using exact Decimal math."""
    raw = "22 MT"
    field_norm = normalize_gross_weight_kg(raw)
    assert field_norm.state == "VALID"
    assert field_norm.value == Decimal("22000")
    assert isinstance(field_norm.value, Decimal)
    assert field_norm.rule_version == RULE_VERSION

    dec_val = to_decimal_kg(raw)
    assert dec_val == Decimal("22000")


def test_ut_norm_005_decimal_gross_weight_representation() -> None:
    """UT-NORM-005: Decimal Gross Weight Representation (DC-04) exact decimal, no IEEE float drift."""
    raw = "22,500.50 KGS"
    field_norm = normalize_gross_weight_kg(raw)
    assert field_norm.state == "VALID"
    assert field_norm.value == Decimal("22500.50")
    assert isinstance(field_norm.value, Decimal)
    assert field_norm.rule_version == RULE_VERSION

    contract_obj = to_normalized_gross_weight(raw)
    assert isinstance(contract_obj, NormalizedGrossWeight)
    assert contract_obj.canonical_kg == Decimal("22500.50")


def test_gross_weight_rejects_binary_float() -> None:
    """Gross weight strictly rejects binary float inputs to ensure lossless Decimal semantics."""
    # Passing a float must be rejected as INVALID; caller must supply str, int, or Decimal
    float_input = 22500.50
    norm = normalize_gross_weight_kg(float_input)
    assert norm.state == "INVALID"
    assert norm.value is None

    # Lossless integer and Decimal inputs are accepted
    norm_int = normalize_gross_weight_kg(22000)
    assert norm_int.state == "VALID"
    assert norm_int.value == Decimal("22000")

    norm_dec = normalize_gross_weight_kg(Decimal("22500.50"))
    assert norm_dec.state == "VALID"
    assert norm_dec.value == Decimal("22500.50")


def test_container_count_discrete_integers_boundary() -> None:
    """Container count value normalizer accepts ONLY already-extracted discrete numeric integer forms."""
    # Clean already-extracted integer forms are VALID
    for raw, expected in [(2, 2), ("2", 2), ("  12  ", 12)]:
        norm = normalize_container_count(raw)
        assert norm.state == "VALID"
        assert norm.value == expected
        assert norm.rule_version == RULE_VERSION


def test_container_count_rejects_labeled_forms_and_semantic_expressions() -> None:
    """Container count value normalizer rejects field labels, descriptive words, and formulas.

    These labeled forms ('2 CONTAINERS', 'QTY: 2') and equipment expressions ('2 X 40HC')
    belong strictly to Stage 3 Extraction / Semantic Interpretation (T10-01).
    """
    for labeled_or_semantic_raw in (
        "2 CONTAINERS",
        "QTY: 2",
        "Total: 2 CTRS",
        "2 X 40HC, 1 X 20GP",
        "1 x 40'HC",
        "Three Containers",
        "Three (3) Containers",
        "Twenty-Two Containers",
        "four containers approx",
        "2 or 3 containers",
        "about 5 units",
        "unknown count",
        "TBD",
        "N/A",
        "",
        "   ",
        None,
        True,
        False,
    ):
        norm = normalize_container_count(labeled_or_semantic_raw)
        assert norm.state == "INVALID"
        assert norm.value is None
        assert norm.rule_version is None


def test_exploratory_semantic_helpers_absent_from_public_api() -> None:
    """Verify that exploratory or quarantined semantic helpers are absent from production normalization API."""
    assert not hasattr(src.normalization, "quarantined_interpret_container_count")
    assert not hasattr(src.normalization, "interpret_container_count")
    assert "quarantined_interpret_container_count" not in src.normalization.__all__


def test_gross_weight_invalid_prose_and_ranges() -> None:
    """Gross weight rejects ambiguous prose and range prose as INVALID."""
    for invalid_raw in (
        "approx 22 MT",
        "22000 or 23000 kg",
        "estimated weight 25000",
        "TBD",
        "N/A",
        "",
        "   ",
        None,
        True,
        False,
    ):
        norm = normalize_gross_weight_kg(invalid_raw)
        assert norm.state == "INVALID"
        assert norm.value is None
        assert norm.rule_version is None


def test_text_normalizer_invalid_inputs() -> None:
    """Text normalizer rejects empty or whitespace-only inputs as INVALID."""
    for invalid_raw in ("", "   ", None):
        norm = normalize_text("shipper", invalid_raw)
        assert norm.state == "INVALID"
        assert norm.value is None
        assert norm.rule_version is None
