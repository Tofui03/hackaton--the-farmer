from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re
from typing import ClassVar

from src.domain.values.base import ValueObject


@dataclass(frozen=True)
class GrossWeight(ValueObject):
    """Immutable domain Value Object representing cargo gross weight normalized to KG.

    Invariants:
    - value: strictly finite Decimal, non-bool, non-float, non-negative/positive.
    - unit: "KG" standard domain canonical unit.
    - Truly immutable, zero setters.
    """

    value: Decimal
    unit: str = "KG"

    # Conversion factor from LBS/LB to KG: 1 lb = 0.45359237 kg
    LBS_TO_KG_FACTOR: ClassVar[Decimal] = Decimal("0.45359237")

    AMBIGUOUS_KEYWORDS: ClassVar[tuple[str, ...]] = (
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

    def __post_init__(self) -> None:
        if isinstance(self.value, bool):
            raise ValueError("GrossWeight value cannot be a boolean")
        if not isinstance(self.value, Decimal):
            raise ValueError(f"GrossWeight value must be a Decimal, got {type(self.value).__name__}")
        if not self.value.is_finite():
            raise ValueError(f"GrossWeight value must be a finite Decimal, got {self.value}")
        if self.value <= Decimal(0):
            raise ValueError(f"GrossWeight value must be greater than 0, got {self.value}")
        if self.unit != "KG":
            raise ValueError(f"GrossWeight standard unit must be 'KG', got '{self.unit}'")

    @classmethod
    def from_input(cls, raw: str | int | float | Decimal | None) -> GrossWeight:
        """Parse raw input, normalize unit to KG, and instantiate GrossWeight.

        Supports:
        - Exact Decimals and Integers (assumed KG if unitless)
        - Strings with units: MT / Metric Tons / T (factor 1000)
        - Strings with units: LBS / LB (factor 0.45359237)
        - Strings with units: KG / KGS / KILOGRAMS
        - Clean numeric strings (assumed KG)

        Guards:
        - Strictly rejects ambiguity words (APPROX, TBD, etc.)
        - Strictly rejects ranges (e.g. 20000 TO 25000)
        - Strictly rejects float (to guard against IEEE precision loss)
        - Strictly rejects booleans, None, and empty strings
        """
        if raw is None:
            raise ValueError("GrossWeight cannot be None")

        if isinstance(raw, bool):
            raise ValueError("GrossWeight cannot be a boolean")

        if isinstance(raw, float):
            raise ValueError("GrossWeight raw binary float is rejected to prevent IEEE precision loss")

        if isinstance(raw, Decimal):
            return cls(value=raw)

        if isinstance(raw, int):
            return cls(value=Decimal(raw))

        if not isinstance(raw, str):
            raise ValueError(f"Unsupported raw input type for GrossWeight: {type(raw).__name__}")

        s = raw.strip().upper()
        if not s:
            raise ValueError("GrossWeight input string cannot be empty")

        # 1. Guard against ambiguous prose
        for kw in cls.AMBIGUOUS_KEYWORDS:
            if re.search(rf"\b{re.escape(kw)}\b", s):
                raise ValueError(f"Ambiguous gross weight keyword detected: '{kw}'")

        # Guard against range / alternation prose
        if re.search(r"\b\d+\s*(?:OR|TO|-)\s*\d+\b", s):
            raise ValueError(f"Range or alternation expression rejected in gross weight: '{raw}'")

        clean_str = s.replace(",", "")

        # 2. Check for MT / Metric Tons / T: MT * 1000 = KG
        mt_match = re.search(
            r"([0-9]+(?:\.[0-9]+)?)\s*(?:MT|METRIC\s*TONS?|M/T|(?<![A-Z])T(?![A-Z]))\b",
            clean_str,
        )
        if mt_match:
            try:
                num_dec = Decimal(mt_match.group(1))
                val = num_dec * Decimal("1000")
                if val == val.to_integral():
                    val = val.quantize(Decimal(1))
                return cls(value=val)
            except InvalidOperation as e:
                raise ValueError(f"Invalid decimal format in MT weight: '{raw}'") from e

        # 3. Check for LBS / LB: LBS * 0.45359237 = KG
        lbs_match = re.search(
            r"([0-9]+(?:\.[0-9]+)?)\s*(?:LBS?|POUNDS?)\b",
            clean_str,
        )
        if lbs_match:
            try:
                num_dec = Decimal(lbs_match.group(1))
                val = num_dec * cls.LBS_TO_KG_FACTOR
                # Normalize trailing zeroes if any
                return cls(value=val)
            except InvalidOperation as e:
                raise ValueError(f"Invalid decimal format in LBS weight: '{raw}'") from e

        # 4. Check for KG / KGS / KILOGRAMS
        kg_match = re.search(
            r"([0-9]+(?:\.[0-9]+)?)\s*(?:KGS?|KILOGRAMS?)\b",
            clean_str,
        )
        if kg_match:
            try:
                val = Decimal(kg_match.group(1))
                return cls(value=val)
            except InvalidOperation as e:
                raise ValueError(f"Invalid decimal format in KG weight: '{raw}'") from e

        # 5. Pure numeric string without explicit unit
        all_numbers = re.findall(r"\b[0-9]+(?:\.[0-9]+)?\b", clean_str)
        if len(all_numbers) == 1:
            try:
                val = Decimal(all_numbers[0])
                return cls(value=val)
            except InvalidOperation as e:
                raise ValueError(f"Invalid decimal format in plain weight: '{raw}'") from e

        raise ValueError(f"Unable to parse gross weight from input: '{raw}'")

    def to_canonical(self) -> Decimal:
        """Return the canonical Decimal representation in KG."""
        return self.value
