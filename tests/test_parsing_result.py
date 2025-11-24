# tests/test_parsing_result.py
from __future__ import annotations

import pytest
from pydantic import BaseModel

from clinch.parsing import ParsingFailure, ParsingResult


class _TestModel(BaseModel):
    value: str


def test_empty_parsing_result_has_zero_counts_and_no_failures() -> None:
    result: ParsingResult[TestModel] = ParsingResult()
    assert result.success_count == 0
    assert result.failure_count == 0
    assert result.has_failures is False


def test_parsing_result_tracks_successes_and_failures() -> None:
    success = _TestModel(value="ok")
    failure = ParsingFailure(
        raw_text="bad line",
        attempted_patterns=["pattern1"],
        exception="error",
        line_number=10,
    )
    result: ParsingResult[TestModel] = ParsingResult(
        successes=[success],
        failures=[failure],
    )
    assert result.success_count == 1
    assert result.failure_count == 1
    assert result.has_failures is True


def test_retry_with_pattern_appends_pattern_and_returns_none() -> None:
    failure = ParsingFailure(
        raw_text="bad",
        attempted_patterns=[],
        exception=None,
        line_number=1,
    )

    failure.retry_with_pattern("new-pattern")

    assert "new-pattern" in failure.attempted_patterns


def test_raise_if_failures_with_failures() -> None:
    from clinch.exceptions import ParsingError

    result = ParsingResult(
        failures=[ParsingFailure(raw_text="bad", attempted_patterns=[], line_number=1)],
    )

    with pytest.raises(ParsingError):
        result.raise_if_failures()


def test_raise_if_failures_no_failures() -> None:
    result = ParsingResult(successes=[TestModel(value="ok")])
    result.raise_if_failures()


def test_filter_successes() -> None:
    result = ParsingResult(
        successes=[
            _TestModel(value="apple"),
            _TestModel(value="banana"),
            _TestModel(value="apricot"),
        ],
    )

    only_a = result.filter_successes(lambda m: m.value.startswith("a"))
    assert [m.value for m in only_a] == ["apple", "apricot"]


def test_map_successes() -> None:
    result = ParsingResult(
        successes=[
            _TestModel(value="one"),
            _TestModel(value="two"),
        ],
    )

    def to_upper(m: _TestModel) -> _TestModel:
        return _TestModel(value=m.value.upper())

    mapped = result.map_successes(to_upper)
    assert [m.value for m in mapped.successes] == ["ONE", "TWO"]
    assert mapped.failures == result.failures


def test_get_failure_lines_and_summary() -> None:
    result = ParsingResult(
        successes=[TestModel(value="ok")],
        failures=[
            ParsingFailure(
                raw_text="bad line",
                attempted_patterns=["pattern"],
                line_number=3,
                exception="validation error",
            )
        ],
    )

    lines = result.get_failure_lines()
    assert lines == [3]

    summary = result.get_failure_summary()
    assert "1 / 2 lines" in summary
    assert "Line 3" in summary
    assert "bad line" in summary
