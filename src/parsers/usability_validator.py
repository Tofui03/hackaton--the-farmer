from __future__ import annotations

"""Document Text Usability Validation Engine (T05-02, DEC-P02).

Implements multi-signal qualitative usability evaluation for parsed documents.
Explicitly rejects arbitrary numeric cutoffs (e.g. len > 20, count >= 50, ratio >= 0.30)
and synthetic-fixture-specific sentinel tokens.
Grounded strictly in generic qualitative criteria: empty stream, scanned PDF,
binary decode replacement corruption, null bytes, and minor localized artifacts.
"""

from typing import Final
from pydantic import BaseModel, ConfigDict
from src.models.document import ParserStatus

# Characters considered valid control whitespace
_VALID_WHITESPACE: Final[set[str]] = {"\r", "\n", "\t"}


class UsabilityAssessment(BaseModel):
    """Result of document usability evaluation."""

    model_config = ConfigDict(extra="forbid", strict=True)

    is_usable: bool
    status: ParserStatus
    is_scanned: bool = False
    reasons: list[str]
    clean_text: str | None = None
    garbage_ratio: float = 0.0
    garbage_count: int = 0
    total_chars: int = 0


def assess_text_usability(
    text: str | None,
    *,
    is_pdf: bool = False,
    page_count: int = 0,
) -> UsabilityAssessment:
    """Qualitatively assess whether extracted text is usable for downstream processing (T05-02).

    Approved Generic Qualitative Evaluation Criteria:
    1. Empty / Missing text:
       - If is_pdf and page_count > 0: marks is_scanned=True, status=UNREADABLE, is_usable=False.
       - Otherwise: status=UNREADABLE, is_usable=False.
    2. Zero Fixed-Length Cutoff (REG-007):
       - Short documents (e.g. 10, 18, or 25 chars) with valid printable characters are accepted
         as USABLE (status=SUCCESS) without triggering OCR or rejection.
    3. Binary Decode Replacement Corruption & Null Bytes (PAR-USAB-002):
       - Replacement characters ('\ufffd') and null bytes ('\x00') signify corrupted binary decoding
         or non-textual payloads. Qualitative signal: status=UNREADABLE, is_usable=False.
    4. Partial Usability with Minor Localized Artifacts (DEC-AI-P04, PAR-USAB-004):
       - When text contains minor non-printable control characters (e.g. printer escapes) but no
         binary decode replacement corruption, content remains usable: status=PARTIAL, is_usable=True,
         with artifacts filtered from clean_text.
    5. Clean Valid Content (PAR-USAB-001):
       - Text without decode corruption or non-printable control artifacts: status=SUCCESS, is_usable=True.
    """
    if text is None or not text.strip():
        if is_pdf and page_count > 0:
            return UsabilityAssessment(
                is_usable=False,
                status=ParserStatus.UNREADABLE,
                is_scanned=True,
                reasons=["empty_text_stream_scanned_pdf"],
                clean_text=None,
                garbage_ratio=0.0,
                garbage_count=0,
                total_chars=0,
            )
        return UsabilityAssessment(
            is_usable=False,
            status=ParserStatus.UNREADABLE,
            is_scanned=False,
            reasons=["empty_text_stream"],
            clean_text=None,
            garbage_ratio=0.0,
            garbage_count=0,
            total_chars=0,
        )

    stripped = text.strip()
    total_chars = len(stripped)

    # 1. Inspect characters for generic qualitative signals and diagnostic measurements
    has_replacement_char = False
    has_null_byte = False
    control_char_count = 0
    garbage_count = 0
    clean_chars: list[str] = []

    for ch in stripped:
        if ch == "\ufffd":
            has_replacement_char = True
            garbage_count += 1
        elif ch == "\x00":
            has_null_byte = True
            garbage_count += 1
        else:
            code = ord(ch)
            if (code < 32 and ch not in _VALID_WHITESPACE) or code == 127:
                control_char_count += 1
                garbage_count += 1
            else:
                clean_chars.append(ch)

    garbage_ratio = garbage_count / total_chars if total_chars > 0 else 0.0

    # 2. Generic Qualitative Signal: Binary decode replacement corruption or null bytes (PAR-USAB-002)
    if has_replacement_char or has_null_byte:
        reasons: list[str] = []
        if has_replacement_char:
            reasons.append("binary_decode_replacement_corruption")
        if has_null_byte:
            reasons.append("binary_null_bytes_present")
        return UsabilityAssessment(
            is_usable=False,
            status=ParserStatus.UNREADABLE,
            is_scanned=False,
            reasons=reasons,
            clean_text=None,
            garbage_ratio=garbage_ratio,
            garbage_count=garbage_count,
            total_chars=total_chars,
        )

    # 3. Generic Qualitative Signal: Minor localized control-character artifacts (PAR-USAB-004)
    if control_char_count > 0:
        return UsabilityAssessment(
            is_usable=True,
            status=ParserStatus.PARTIAL,
            is_scanned=False,
            reasons=[f"minor_control_character_artifacts_count_{control_char_count}"],
            clean_text="".join(clean_chars).strip(),
            garbage_ratio=garbage_ratio,
            garbage_count=garbage_count,
            total_chars=total_chars,
        )

    # 4. Generic Qualitative Signal: Clean, fully usable document (PAR-USAB-001, REG-007)
    return UsabilityAssessment(
        is_usable=True,
        status=ParserStatus.SUCCESS,
        is_scanned=False,
        reasons=[],
        clean_text=stripped,
        garbage_ratio=0.0,
        garbage_count=0,
        total_chars=total_chars,
    )
