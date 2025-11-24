# src/clinch/parsing/result.py
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

from clinch.fields import Field

T = TypeVar("T")


class ParsingFailure(BaseModel):
    raw_text: str = Field(description="Original line that failed to parse")
    attempted_patterns: list[str] = Field(description="Regex patterns that were tried")
    exception: str | None = Field(default=None, description="Exception message if any")
    line_number: int = Field(description="Line number in output (1-indexed)")

    def retry_with_pattern(self, pattern: str) -> None:
        self.attempted_patterns.append(pattern)


class ParsingResult(BaseModel, Generic[T]):
    successes: list[T] = Field(default_factory=list, description="Successfully parsed instances")
    failures: list[ParsingFailure] = Field(default_factory=list, description="Failed parsing attempts")

    @property
    def has_failures(self) -> bool:
        return len(self.failures) > 0

    @property
    def success_count(self) -> int:
        return len(self.successes)

    @property
    def failure_count(self) -> int:
        return len(self.failures)
