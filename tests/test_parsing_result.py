# tests/test_parsing_result.py
from __future__ import annotations

from typing import List

from pydantic import BaseModel

from clinch.parsing import ParsingFailure, ParsingResult


class DummyResponse(BaseModel):
    value: str


def test_empty_parsing_result_has_zero_counts_and_no_failures() -> None:
    result: ParsingResult[DummyResponse] = ParsingResult()
    assert result.successes == []
    assert result.failures == []
    assert result.success_count == 0
    assert result.failure_count == 0
    assert result.has_failures is False


def test_parsing_result_tracks_successes_and_failures() -> None:
    successes: List[DummyResponse] = [
        DummyResponse(value="one"),
        DummyResponse(value="two"),
    ]
    failure = ParsingFailure(
        raw_text="invalid line",
        attempted_patterns=["pattern1"],
        exception="some error",
        line_number=3,
    )

    result: ParsingResult[DummyResponse] = ParsingResult(
        successes=successes,
        failures=[failure],
    )

    assert result.success_count == 2
    assert result.failure_count == 1
    assert result.has_failures is True
    assert result.successes[0].value == "one"
    assert result.failures[0].raw_text == "invalid line"


def test_parsing_failure_fields_roundtrip() -> None:
    failure = ParsingFailure(
        raw_text="bad line",
        attempted_patterns=["patternA", "patternB"],
        exception=None,
        line_number=10,
    )

    assert failure.raw_text == "bad line"
    assert failure.attempted_patterns == ["patternA", "patternB"]
    assert failure.exception is None
    assert failure.line_number == 10


def test_retry_with_pattern_appends_pattern_and_returns_none() -> None:
    failure = ParsingFailure(
        raw_text="bad",
        attempted_patterns=[],
        exception=None,
        line_number=1,
    )

    result = failure.retry_with_pattern("new-pattern")

    assert result is None
    assert "new-pattern" in failure.attempted_patterns
