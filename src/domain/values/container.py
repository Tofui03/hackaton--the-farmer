from __future__ import annotations

from dataclasses import dataclass
import re

from src.domain.values.base import ValueObject


@dataclass(frozen=True)
class ContainerCount(ValueObject):
    """Immutable domain Value Object representing container count.

    Invariants:
    - Must be a strictly positive integer (> 0).
    - Rejects booleans, floats, non-numeric strings, negative numbers, and zero.
    """

    value: int

    def __post_init__(self) -> None:
        # In Python, bool is a subclass of int (isinstance(True, int) == True)
        if type(self.value) is not int:
            raise ValueError(f"Container count must be an integer, got {type(self.value).__name__}")
        if self.value <= 0:
            raise ValueError(f"Container count must be greater than 0, got {self.value}")

    @classmethod
    def from_input(cls, raw: str | int | None) -> ContainerCount:
        """Parse, validate, and instantiate ContainerCount from raw input.

        Encapsulates integer validation and boundary protection.
        """
        if raw is None:
            raise ValueError("Container count cannot be None")

        if isinstance(raw, bool):
            raise ValueError("Container count cannot be a boolean")

        if isinstance(raw, float):
            raise ValueError("Container count cannot be a float")

        if isinstance(raw, int):
            return cls(value=raw)

        if isinstance(raw, str):
            s = raw.strip()
            if not s:
                raise ValueError("Container count cannot be empty string")
            if not re.fullmatch(r"[0-9]+", s):
                raise ValueError(f"Invalid container count representation: '{raw}'")
            val = int(s)
            return cls(value=val)

        raise ValueError(f"Unsupported container count type: {type(raw).__name__}")

    def to_canonical(self) -> int:
        """Return the canonical integer value."""
        return self.value
