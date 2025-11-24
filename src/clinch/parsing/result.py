# src/clinch/parsing/result.py
from __future__ import annotations

from typing import Any, Generic, Iterable, List, TypeVar

from pydantic import BaseModel, Field

TModel = TypeVar("TModel")


class ParsingFailure(BaseModel):
    raw_text: str
    line_number: int
    attempted_patterns: List[str] = Field(default_factory=list)
    exception: Any | None = None
    pattern_name: str | None = None
    pattern: str | None = None
    message: str | None = None

    model_config = {
        "arbitrary_types_allowed": True,
    }

    def retry_with_pattern(self, pattern: str) -> None:
        """Record an additional pattern we tried when re-parsing this line."""
        self.attempted_patterns.append(pattern)


class ParsingResult(Generic[TModel], BaseModel):
    successes: List[TModel] = Field(default_factory=list)
    failures: List[ParsingFailure] = Field(default_factory=list)

    model_config = {
        "arbitrary_types_allowed": True,
    }

    @property
    def success_count(self) -> int:
        return len(self.successes)

    @property
    def failure_count(self) -> int:
        return len(self.failures)

    @property
    def has_failures(self) -> bool:
        return bool(self.failures)

    def iter_successes(self) -> Iterable[TModel]:
        return iter(self.successes)

    def iter_failures(self) -> Iterable[ParsingFailure]:
        return iter(self.failures)
