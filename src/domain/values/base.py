from abc import ABC
from dataclasses import dataclass


@dataclass(frozen=True)
class ValueObject(ABC):
    """Immutable base class for all Domain Value Objects in DDD.

    Invariants:
    - Truly immutable (frozen=True, zero setters).
    - Structural equality based on values.
    """

    pass
