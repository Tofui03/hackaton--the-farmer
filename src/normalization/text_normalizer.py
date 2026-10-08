from __future__ import annotations

import re
import unicodedata
from typing import Final

from src.domain.values import NormalizedText
from src.models.extraction import FieldName, NormalizedField

RULE_VERSION: Final[str] = "norm-v1.0"


def normalize_unicode(text: str) -> str:
    """Normalize unicode characters using standard NFKC form (DEC-P06A).

    Converts full-width characters, typographic variants, etc. to standard Unicode/ASCII.
    Example: 'ＳＨＡＮＧＨＡＩ' -> 'SHANGHAI'
    """
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text)


def clean_punctuation(text: str) -> str:
    """Standardize quotation marks and trim trailing sentence/field punctuation (DEC-P06A).

    - Standardizes curly/typographical quotes to standard straight quotes.
    - Trims trailing periods, commas, semicolons, colons.
    - Preserves internal punctuation, internal commas, address structure, token order,
      and corporate entity suffixes untouched.
    """
    if not text:
        return ""
    # Standardize double quotes
    s = (
        text.replace("“", '"')
        .replace("”", '"')
        .replace("«", '"')
        .replace("»", '"')
        .replace("„", '"')
        .replace("‟", '"')
    )
    # Standardize single quotes
    s = (
        s.replace("‘", "'")
        .replace("’", "'")
        .replace("‚", "'")
        .replace("‛", "'")
        .replace("‹", "'")
        .replace("›", "'")
    )
    # Trim trailing punctuation (dots, commas, semicolons, colons) and trailing whitespace only.
    # Internal punctuation and tokens are strictly preserved.
    s = re.sub(r"[\s.,;:]+$", "", s)
    return s


def normalize_whitespace_and_case(text: str) -> str:
    """Collapse internal whitespace, trim edges, and fold case to uppercase (DEC-P06A).

    Example: '  Acme   Industrial   Corp.  ' -> 'ACME INDUSTRIAL CORP.'
    """
    if not text:
        return ""
    s = re.sub(r"\s+", " ", text).strip()
    return s.upper()


def normalize_text(field: FieldName, raw_value: str | None) -> NormalizedField:
    """Normalize raw text using domain NormalizedText Value Object (DEC-P06A)."""
    if raw_value is None or not isinstance(raw_value, str):
        return NormalizedField(
            field=field,
            state="INVALID",
            value=None,
            rule_version=None,
        )
    try:
        val_obj = NormalizedText.from_raw(raw_value)
        return NormalizedField(
            field=field,
            state="VALID",
            value=val_obj.to_canonical(),
            rule_version=RULE_VERSION,
        )
    except ValueError:
        return NormalizedField(
            field=field,
            state="INVALID",
            value=None,
            rule_version=None,
        )
