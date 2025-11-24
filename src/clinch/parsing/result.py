# src/clinch/parsing/result.py
from __future__ import annotations

from typing import Callable, Generic, TypeVar

from pydantic import BaseModel

from clinch.fields import Field

T = TypeVar("T")


class ParsingFailure(BaseModel):
    """Details about a single parsing failure."""

    raw_text: str = Field(description="Original line that failed to parse")
    attempted_patterns: list[str] = Field(
        default_factory=list,
        description="Patterns that were tried against this line",
    )
    exception: str | None = Field(
        default=None,
        description="Validation or parsing error details, if any",
    )
    line_number: int = Field(description="1-based line number in the original output")


class ParsingResult(BaseModel, Generic[T]):
    """Container for parsing results.

    Holds successfully parsed instances and information about any
    failures that occurred during parsing.
    """

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
        return len(self.failures) > 0

    @property
    def success_count(self) -> int:
        return len(self.successes)

    @property
    def failure_count(self) -> int:
        return len(self.failures)

    # Helper methods (Step 4 of refactoring roadmap)

    def raise_if_failures(self) -> None:
        """Raise ParsingError if any failures occurred."""
        if self.has_failures:
            from clinch.exceptions import ParsingError

            raise ParsingError(self.failures)

    def filter_successes(self, predicate: Callable[[T], bool]) -> list[T]:
        """Filter successful results by predicate."""
        return [s for s in self.successes if predicate(s)]

    def map_successes(self, func: Callable[[T], T]) -> ParsingResult[T]:
        """Transform successful results, preserving failures."""
        return ParsingResult(
            successes=[func(s) for s in self.successes],
            failures=self.failures.copy(),
        )

    def get_failure_lines(self) -> list[int]:
        """Get line numbers of all failures."""
        return [f.line_number for f in self.failures]

    def get_failure_summary(self) -> str:
        """Get human-readable failure summary."""
        if not self.failures:
            return "No parsing failures"

        total = self.success_count + self.failure_count
        lines: list[str] = [
            f"Parsing Failures: {self.failure_count} / {total} lines",
            "",
        ]

        for failure in self.failures[:5]:
            lines.append(f"Line {failure.line_number}: {failure.raw_text[:60]}")
            if failure.exception:
                lines.append(f"  Error: {failure.exception[:100]}")

        if len(self.failures) > 5:
            lines.append(f"... and {len(self.failures) - 5} more failures")

        return "\n".join(lines)
