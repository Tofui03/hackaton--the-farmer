from __future__ import annotations

import re
import unicodedata
from typing import Final

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
    """Deterministically normalize shipping text fields (shipper, consignee, ports, etc.).

    Pipeline:
    1. Unicode NFKC normalization
    2. Punctuation standardization and trailing punctuation trimming
    3. Whitespace collapsing and uppercase folding

    Strict Guardrails:
    - Do NOT strip legal entity suffixes (LTD, CORP, INC, etc.) per DEC-P06D.
    - Do NOT map port aliases or codes (SHANGHAI != PORT OF SHANGHAI) per DEC-P06C.
    - Preserve internal token order and address lines.
    """
    if raw_value is None or not isinstance(raw_value, str):
        return NormalizedField(
            field=field,
            state="INVALID",
            value=None,
            rule_version=None,
        )

    # 1. Unicode NFKC
    val = normalize_unicode(raw_value)
    # 2. Punctuation cleanup (quotes & trailing punctuation)
    val = clean_punctuation(val)
    # 3. Spacing & Case folding
    val = normalize_whitespace_and_case(val)

    if not val:
        return NormalizedField(
            field=field,
            state="INVALID",
            value=None,
            rule_version=None,
        )

    return NormalizedField(
        field=field,
        state="VALID",
        value=val,
        rule_version=RULE_VERSION,
    )
