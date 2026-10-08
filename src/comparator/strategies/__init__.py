from __future__ import annotations

from src.comparator.strategies.base import FieldComparisonStrategy
from src.comparator.strategies.implementations import (
    ContainerCountStrategy,
    GrossWeightStrategy,
    TextExactStrategy,
)
from src.comparator.strategies.registry import (
    DEFAULT_STRATEGY_REGISTRY,
    ComparisonStrategyRegistry,
)

__all__ = [
    "FieldComparisonStrategy",
    "TextExactStrategy",
    "ContainerCountStrategy",
    "GrossWeightStrategy",
    "ComparisonStrategyRegistry",
    "DEFAULT_STRATEGY_REGISTRY",
]
