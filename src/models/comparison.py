from __future__ import annotations

from enum import Enum
from typing import Literal, Self
from pydantic import model_validator
from src.models.base import Contract, Text, require
from src.models.extraction import Canonical, FIELD_NAMES, FieldName


class ComparisonOutcome(str, Enum):
    """Authoritative comparison outcome."""

    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    NOT_APPLICABLE = "NOT_APPLICABLE"


OutcomeType = Literal["MATCH", "MISMATCH", "NOT_APPLICABLE"]


class FieldComparison(Contract):
    """Structural representation of comparison output between SI and BL for a reliable field."""

    field: FieldName
    si_value: Canonical
    bl_value: Canonical
    outcome: Literal["MATCH", "MISMATCH"]
    rule_version: Text

    @property
    def field_name(self) -> FieldName:
        return self.field


class Discrepancy(Contract):
    """A confirmed difference between SI and BL for a comparison field."""

    field: FieldName
    si_value: Canonical
    bl_value: Canonical

    @property
    def field_name(self) -> FieldName:
        return self.field


class PartialResult(Contract):
    """Disjoint partition of 7 mandatory fields into compared pairs and unresolved fields."""

    comparisons: list[FieldComparison]
    unresolved_fields: list[FieldName]

    @model_validator(mode="after")
    def partition(self) -> Self:
        compared = [item.field for item in self.comparisons]
        require(len(compared) == len(set(compared)), "duplicate comparison")
        require(len(self.unresolved_fields) == len(set(self.unresolved_fields)), "duplicate unresolved field")
        require(not set(compared).intersection(self.unresolved_fields), "compared field cannot be unresolved")
        require(set(compared).union(self.unresolved_fields) == set(FIELD_NAMES), "partial result must partition seven fields")
        return self
