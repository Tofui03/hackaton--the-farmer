from __future__ import annotations

from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field

Text = Annotated[str, Field(min_length=1)]


class Contract(BaseModel):
    """Base contract enforcing strict validation and forbidding extra properties."""

    model_config = ConfigDict(extra="forbid", strict=True)


def require(condition: bool, message: str) -> None:
    """Helper invariant assertion for Pydantic validators."""
    if not condition:
        raise ValueError(message)
