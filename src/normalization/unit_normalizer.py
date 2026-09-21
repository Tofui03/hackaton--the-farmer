from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re
from typing import Final

from src.models.extraction import NormalizedField, NormalizedGrossWeight

RULE_VERSION: Final[str] = "norm-v1.0"

AMBIGUOUS_KEYWORDS: Final[tuple[str, ...]] = (
    "APPROX",
    "APPROXIMATELY",
    "ABOUT",
    "ESTIMATED",
    "EST.",
    "ROUGHLY",
    "UNKNOWN",
    "TBD",
    "N/A",
    "NONE",
    "PENDING",
)


def _clean_decimal_integral(d: Decimal) -> Decimal:
    """If decimal has no fractional component, return as integer Decimal (e.g. 22000.0 -> 22000)."""
    if d == d.to_integral():
        return d.quantize(Decimal(1))
    return d


def normalize_container_count(raw_value: str | int | None) -> NormalizedField:
    """Deterministically normalize container count to a strict integer (DEC-P06B).

    SCOPE & BOUNDARY:
    This is a pure VALUE NORMALIZER. It maps already-extracted discrete numeric
    representations to canonical strict `int`. It does NOT strip field labels
    (e.g. 'QTY:'), unit words (e.g. 'CONTAINERS'), interpret English number words,
    or perform equipment notation aggregation (e.g. '2 X 40HC, 1 X 20GP'). Those
    responsibilities belong strictly to Stage 3 Extraction (T10-01).

    Accepts:
    - Pure integer inputs (2 -> 2)
    - Clean numeric strings ('2' -> 2, '  12  ' -> 12)

    Rejects:
    - Strings containing field labels or descriptive words ('2 CONTAINERS', 'QTY: 2' -> INVALID)
    - Equipment notations and arithmetic expressions ('2 X 40HC, 1 X 20GP' -> INVALID)
    - English spelled words ('Three Containers' -> INVALID)
    - Ambiguous prose ('four containers approx' -> INVALID)
    - Range / alternation prose ('2 or 3 containers' -> INVALID)
    - Python booleans (True/False -> INVALID)
    - Missing or non-numeric values (None, '' -> INVALID)
    """
    if raw_value is None:
        return NormalizedField(
            field="container_count",
            state="INVALID",
            value=None,
            rule_version=None,
        )

    # Boolean is an int subclass in Python; reject explicitly
    if isinstance(raw_value, bool):
        return NormalizedField(
            field="container_count",
            state="INVALID",
            value=None,
            rule_version=None,
        )

    if isinstance(raw_value, int):
        return NormalizedField(
            field="container_count",
            state="VALID",
            value=raw_value,
            rule_version=RULE_VERSION,
        )

    if not isinstance(raw_value, str):
        return NormalizedField(
            field="container_count",
            state="INVALID",
            value=None,
            rule_version=None,
        )

    s = raw_value.strip()
    if not s:
        return NormalizedField(
            field="container_count",
            state="INVALID",
            value=None,
            rule_version=None,
        )

    # Value normalizer accepts already-extracted integer digit strings only (e.g. '2', '  12  ')
    if re.fullmatch(r"-?[0-9]+", s):
        val = int(s)
        return NormalizedField(
            field="container_count",
            state="VALID",
            value=val,
            rule_version=RULE_VERSION,
        )

    # Labeled forms ('2 CONTAINERS', 'QTY: 2'), equipment formulas, spelled words,
    # and ambiguous prose are rejected by the value normalizer.
    return NormalizedField(
        field="container_count",
        state="INVALID",
        value=None,
        rule_version=None,
    )


def normalize_gross_weight_kg(
    raw_value: str | int | Decimal | None,
) -> NormalizedField:
    """Deterministically normalize gross cargo weight to exact Decimal kilograms (DEC-P06B, DC-04).

    LOSSLESS SEMANTICS REQUIREMENT:
    To ensure zero IEEE floating-point precision loss, raw binary `float` input is
    STRICTLY REJECTED. Only lossless input types (`str`, `int`, `Decimal`) are accepted.

    Handles:
    - MT to KG conversion: MT * 1000 = KG using exact Decimal arithmetic ('22 MT' -> Decimal('22000'))
    - Comma thousand-separators ('25,432.50 KGS' -> Decimal('25432.50'))
    - Clean numeric strings ('22000 kg' -> Decimal('22000'), '22000' -> Decimal('22000'))
    - Strict integers and finite Decimals (22000 -> Decimal('22000'))

    Rejects:
    - Raw binary floats (e.g. 22500.50 -> INVALID; binary float may have already lost precision)
    - Ambiguous prose ('approx 22 MT' -> INVALID)
    - Range / alternation prose ('22000 or 23000 kg' -> INVALID)
    - Python booleans (True/False -> INVALID)
    - Missing, empty, or unparseable input (None, '' -> INVALID)
    """
    if raw_value is None:
        return NormalizedField(
            field="gross_weight_kg",
            state="INVALID",
            value=None,
            rule_version=None,
        )

    # Boolean is an int subclass in Python; reject explicitly
    if isinstance(raw_value, bool):
        return NormalizedField(
            field="gross_weight_kg",
            state="INVALID",
            value=None,
            rule_version=None,
        )

    # Binary float is explicitly rejected to prevent silent IEEE precision loss
    if isinstance(raw_value, float):
        return NormalizedField(
            field="gross_weight_kg",
            state="INVALID",
            value=None,
            rule_version=None,
        )

    if isinstance(raw_value, Decimal):
        if raw_value.is_finite():
            return NormalizedField(
                field="gross_weight_kg",
                state="VALID",
                value=raw_value,
                rule_version=RULE_VERSION,
            )
        return NormalizedField(
            field="gross_weight_kg",
            state="INVALID",
            value=None,
            rule_version=None,
        )

    if isinstance(raw_value, int):
        return NormalizedField(
            field="gross_weight_kg",
            state="VALID",
            value=Decimal(raw_value),
            rule_version=RULE_VERSION,
        )

    if not isinstance(raw_value, str):
        return NormalizedField(
            field="gross_weight_kg",
            state="INVALID",
            value=None,
            rule_version=None,
        )

    s = raw_value.strip().upper()
    if not s:
        return NormalizedField(
            field="gross_weight_kg",
            state="INVALID",
            value=None,
            rule_version=None,
        )

    # 1. Reject ambiguous prose
    for kw in AMBIGUOUS_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", s):
            return NormalizedField(
                field="gross_weight_kg",
                state="INVALID",
                value=None,
                rule_version=None,
            )

    # Reject range/alternation prose (e.g. '22000 or 23000 kg')
    if re.search(r"\b\d+\s+(?:OR|TO|-)\s+\d+\b", s):
        return NormalizedField(
            field="gross_weight_kg",
            state="INVALID",
            value=None,
            rule_version=None,
        )

    # Remove thousand-separator commas
    clean_str = s.replace(",", "")

    # 2. Check for MT (Metric Tons) conversion: MT * 1000 = KG
    mt_match = re.search(
        r"([0-9]+(?:\.[0-9]+)?)\s*(?:MT|METRIC\s*TONS?|TONS?|M/T)\b",
        clean_str,
    )
    if mt_match:
        try:
            num_dec = Decimal(mt_match.group(1))
            val = _clean_decimal_integral(num_dec * Decimal("1000"))
            if val.is_finite():
                return NormalizedField(
                    field="gross_weight_kg",
                    state="VALID",
                    value=val,
                    rule_version=RULE_VERSION,
                )
        except InvalidOperation:
            pass
        return NormalizedField(
            field="gross_weight_kg",
            state="INVALID",
            value=None,
            rule_version=None,
        )

    # 3. Check for KG / KGS / KILOGRAMS
    kg_match = re.search(
        r"([0-9]+(?:\.[0-9]+)?)\s*(?:KGS?|KILOGRAMS?)\b",
        clean_str,
    )
    if kg_match:
        try:
            val = Decimal(kg_match.group(1))
            if val.is_finite():
                return NormalizedField(
                    field="gross_weight_kg",
                    state="VALID",
                    value=val,
                    rule_version=RULE_VERSION,
                )
        except InvalidOperation:
            pass
        return NormalizedField(
            field="gross_weight_kg",
            state="INVALID",
            value=None,
            rule_version=None,
        )

    # 4. Pure single number in text (e.g. '22000', '22500.50')
    all_numbers = re.findall(r"\b[0-9]+(?:\.[0-9]+)?\b", clean_str)
    if len(all_numbers) == 1:
        try:
            val = Decimal(all_numbers[0])
            if val.is_finite():
                return NormalizedField(
                    field="gross_weight_kg",
                    state="VALID",
                    value=val,
                    rule_version=RULE_VERSION,
                )
        except InvalidOperation:
            pass

    return NormalizedField(
        field="gross_weight_kg",
        state="INVALID",
        value=None,
        rule_version=None,
    )


def to_decimal_kg(
    raw_value: str | int | Decimal | None,
) -> Decimal | None:
    """Convenience helper returning the raw Decimal kg value or None if invalid."""
    res = normalize_gross_weight_kg(raw_value)
    if res.state == "VALID" and isinstance(res.value, Decimal):
        return res.value
    return None


def to_normalized_gross_weight(
    raw_value: str | int | Decimal | None,
) -> NormalizedGrossWeight | None:
    """Convenience helper returning a NormalizedGrossWeight contract instance or None."""
    d = to_decimal_kg(raw_value)
    if d is not None:
        return NormalizedGrossWeight(canonical_kg=d)
    return None
