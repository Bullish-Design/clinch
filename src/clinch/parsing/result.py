# src/clinch/parsing/result.py
from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Generic, TypeVar, overload

from pydantic import BaseModel

from clinch.fields import Field

T = TypeVar("T")
U = TypeVar("U")


class ParsingFailure(BaseModel):
    """Details about a single parsing failure."""

    raw_text: str = Field(description="Original line that failed to parse")
    attempted_patterns: list[str] = Field(description="Regex patterns that were tried")
    exception: str | None = Field(
        default=None,
        description="Exception message if any",
    )
    line_number: int = Field(description="Line number in output (1-indexed)")

    def retry_with_pattern(self, pattern: str) -> None:
        """Record an additional attempted pattern."""
        self.attempted_patterns.append(pattern)


class ParsingResult(BaseModel, Generic[T]):  # noqa: UP046
    """Container for parsing results with success/failure tracking.

    Supports iteration and length checks over successes for convenience::

        result = SomeResponse.parse_output(output)
        for item in result:
            print(item)
        print(f"Got {len(result)} results")
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

    def __iter__(self) -> Iterator[T]:  # type: ignore[override]
        """Iterate over successfully parsed instances."""
        return iter(self.successes)

    def __len__(self) -> int:
        """Return the number of successfully parsed instances."""
        return len(self.successes)

    @overload
    def __getitem__(self, index: int) -> T: ...
    @overload
    def __getitem__(self, index: slice) -> list[T]: ...

    def __getitem__(self, index: int | slice) -> T | list[T]:
        """Access successfully parsed instances by index or slice."""
        return self.successes[index]

    def raise_if_failures(self) -> None:
        """Raise ParsingError if any failures occurred."""
        if self.has_failures:
            from clinch.exceptions import ParsingError

            raise ParsingError(self.failures)

    def filter_successes(self, predicate: Callable[[T], bool]) -> list[T]:
        """Filter successful results by predicate."""
        return [s for s in self.successes if predicate(s)]

    def map_successes(self, func: Callable[[T], U]) -> ParsingResult[U]:
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
