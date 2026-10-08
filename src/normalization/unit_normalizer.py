from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re
from typing import Final

from src.domain.values import ContainerCount, GrossWeight
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
    """Deterministically normalize container count using ContainerCount Value Object (DEC-P06B)."""
    try:
        vo = ContainerCount.from_input(raw_value)
        return NormalizedField(
            field="container_count",
            state="VALID",
            value=vo.to_canonical(),
            rule_version=RULE_VERSION,
        )
    except ValueError:
        return NormalizedField(
            field="container_count",
            state="INVALID",
            value=None,
            rule_version=None,
        )


def normalize_gross_weight_kg(
    raw_value: str | int | Decimal | None,
) -> NormalizedField:
    """Deterministically normalize gross cargo weight using GrossWeight Value Object (DEC-P06B, DC-04)."""
    try:
        vo = GrossWeight.from_input(raw_value)
        return NormalizedField(
            field="gross_weight_kg",
            state="VALID",
            value=vo.to_canonical(),
            rule_version=RULE_VERSION,
        )
    except ValueError:
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
