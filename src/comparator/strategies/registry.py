from __future__ import annotations

from typing import Final

from src.comparator.strategies.base import FieldComparisonStrategy
from src.comparator.strategies.implementations import (
    ContainerCountStrategy,
    GrossWeightStrategy,
    TextExactStrategy,
)
from src.models.extraction import FIELD_NAMES, FieldName


class ComparisonStrategyRegistry:
    """Registry maintaining field-to-strategy dispatching."""

    def __init__(self) -> None:
        self._strategies: dict[FieldName, FieldComparisonStrategy] = {}
        self._initialize_defaults()

    def _initialize_defaults(self) -> None:
        for field in FIELD_NAMES:
            if field == "container_count":
                self._strategies[field] = ContainerCountStrategy()
            elif field == "gross_weight_kg":
                self._strategies[field] = GrossWeightStrategy()
            else:
                self._strategies[field] = TextExactStrategy(field)

    def get_strategy(self, field: FieldName) -> FieldComparisonStrategy:
        if field not in self._strategies:
            raise KeyError(f"No comparison strategy registered for field: '{field}'")
        return self._strategies[field]

    def register(self, strategy: FieldComparisonStrategy) -> None:
        """Allow runtime extension/override (Open-Closed Principle)."""
        self._strategies[strategy.target_field] = strategy


# Global default registry instance
DEFAULT_STRATEGY_REGISTRY: Final[ComparisonStrategyRegistry] = ComparisonStrategyRegistry()
