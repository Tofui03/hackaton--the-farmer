from __future__ import annotations

from decimal import Decimal

from src.comparator.strategies.base import FieldComparisonStrategy
from src.models.extraction import Canonical, FieldName, validate_canonical


class TextExactStrategy(FieldComparisonStrategy):
    """Exact deterministic equality strategy for textual fields.

    Handles: shipper, consignee, notify_party, port_of_loading, port_of_discharge.
    """

    def __init__(self, field: FieldName) -> None:
        valid_text_fields: set[FieldName] = {
            "shipper",
            "consignee",
            "notify_party",
            "port_of_loading",
            "port_of_discharge",
        }
        if field not in valid_text_fields:
            raise ValueError(f"TextExactStrategy cannot handle field '{field}'")
        self._target_field: FieldName = field

    @property
    def target_field(self) -> FieldName:
        return self._target_field

    def are_equal(self, si_val: Canonical, bl_val: Canonical) -> bool:
        validate_canonical(self.target_field, si_val)
        validate_canonical(self.target_field, bl_val)
        if not isinstance(si_val, str) or not isinstance(bl_val, str):
            raise ValueError(f"{self.target_field} canonical value must be a string")
        return si_val == bl_val


class ContainerCountStrategy(FieldComparisonStrategy):
    """Exact deterministic integer equality strategy for container_count."""

    @property
    def target_field(self) -> FieldName:
        return "container_count"

    def are_equal(self, si_val: Canonical, bl_val: Canonical) -> bool:
        validate_canonical(self.target_field, si_val)
        validate_canonical(self.target_field, bl_val)
        if type(si_val) is not int or type(bl_val) is not int:
            raise ValueError("container_count canonical values must be integers, not booleans or other types")
        return si_val == bl_val


class GrossWeightStrategy(FieldComparisonStrategy):
    """Strict finite Decimal mathematical equality strategy for gross_weight_kg."""

    @property
    def target_field(self) -> FieldName:
        return "gross_weight_kg"

    def are_equal(self, si_val: Canonical, bl_val: Canonical) -> bool:
        validate_canonical(self.target_field, si_val)
        validate_canonical(self.target_field, bl_val)

        if not isinstance(si_val, Decimal) or isinstance(si_val, bool) or not si_val.is_finite():
            raise ValueError("gross_weight_kg canonical value must be a finite Decimal, not string or float")
        if not isinstance(bl_val, Decimal) or isinstance(bl_val, bool) or not bl_val.is_finite():
            raise ValueError("gross_weight_kg canonical value must be a finite Decimal, not string or float")

        return si_val == bl_val
