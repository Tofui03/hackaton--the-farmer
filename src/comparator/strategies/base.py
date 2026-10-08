from __future__ import annotations

from abc import ABC, abstractmethod

from src.models.extraction import Canonical, FieldName


class FieldComparisonStrategy(ABC):
    """Abstract base class for pure domain field comparison strategies.

    Encapsulates comparison logic and invariant validation for specific field types,
    free from external framework, network, or database dependencies.
    """

    @property
    @abstractmethod
    def target_field(self) -> FieldName:
        """The canonical field name that this strategy handles."""
        ...

    @abstractmethod
    def are_equal(self, si_val: Canonical, bl_val: Canonical) -> bool:
        """Evaluate deterministic equality between SI and BL canonical values.

        Must perform input validity and invariant checks, raising ValueError
        on invalid inputs.
        """
        ...
