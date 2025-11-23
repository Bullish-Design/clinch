# src/clinch/parsing/result.py
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

from clinch.fields import Field

T = TypeVar("T")


class ParsingFailure(BaseModel):
    """Details about a single parsing failure."""

    raw_text: str = Field(description="Original line that failed to parse")
    attempted_patterns: list[str] = Field(description="Regex patterns that were tried")
    exception: str | None = Field(default=None, description="Exception message if any")
    line_number: int = Field(description="Line number in output (1-indexed)")

    def retry_with_pattern(self, pattern: str) -> T | None:
        """Retry parsing with an alternative pattern.

        Actual parsing logic will be provided by the parsing engine in a
        later step. For now, this method records the attempted pattern and
        returns None to signal no re-parse was performed.
        """
        self.attempted_patterns.append(pattern)
        return None


class ParsingResult(BaseModel, Generic[T]):
    """Container for parsing results with success/failure tracking."""

    successes: list[T] = Field(
        default_factory=list,
        description="Successfully parsed instances",
    )
    failures: list[ParsingFailure] = Field(
        default_factory=list,
        description="Failed parsing attempts",
    )

    @property
    def has_failures(self) -> bool:
        """True if any parsing failures occurred."""
        return len(self.failures) > 0

    @property
    def success_count(self) -> int:
        """Number of successful parses."""
        return len(self.successes)

    @property
    def failure_count(self) -> int:
        """Number of failed parses."""
        return len(self.failures)
