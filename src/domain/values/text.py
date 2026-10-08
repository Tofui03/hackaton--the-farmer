from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from src.domain.values.base import ValueObject


@dataclass(frozen=True)
class NormalizedText(ValueObject):
    """Immutable domain Value Object for normalized text fields (DEC-P06A).

    Applies deterministic pipeline upon instantiation/from_raw:
    1. Unicode NFKC normalization (full-width -> standard ASCII)
    2. Punctuation standardization (curly quotes -> straight quotes)
    3. Trim trailing punctuation (. , ; :) while preserving internal commas & dots
    4. Collapse internal whitespace and fold case to UPPERCASE
    """

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise ValueError(f"NormalizedText value must be a str, got {type(self.value).__name__}")
        if not self.value.strip():
            raise ValueError("NormalizedText value cannot be empty or whitespace-only")

    @classmethod
    def from_raw(cls, raw: str | None) -> NormalizedText:
        """Factory method applying the canonical DEC-P06A text normalization pipeline."""
        if raw is None or not isinstance(raw, str):
            raise ValueError("Raw input must be a non-null string")

        # 1. Unicode NFKC
        text = unicodedata.normalize("NFKC", raw)

        # 2. Quotation normalization
        for q in ("“", "”", "«", "»", "„", "‟"):
            text = text.replace(q, '"')
        for q in ("‘", "’", "‚", "‛", "‹", "›"):
            text = text.replace(q, "'")

        # 3. Trim trailing punctuation (. , ; :) and trailing whitespace
        text = re.sub(r"[\s.,;:]+$", "", text)

        # 4. Collapse whitespace and uppercase
        text = " ".join(text.split()).upper()

        if not text:
            raise ValueError("Normalized text evaluated to empty string")

        return cls(value=text)

    def to_canonical(self) -> str:
        return self.value
