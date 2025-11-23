# tests/test_parsing_engine.py
from __future__ import annotations

from typing import Iterable

from clinch import BaseCLIResponse, Field
from clinch.parsing import ParsingResult
from clinch.parsing.engine import parse_output


class SimpleResponse(BaseCLIResponse):
    value: str = Field(pattern=r"value: (\w+)")


class IntResponse(BaseCLIResponse):
    count: int = Field(pattern=r"count: (\S+)")


def test_engine_parses_successes_and_failures_from_string_output() -> None:
    output = "value: first\ninvalid line\nvalue: second"
    result = parse_output(SimpleResponse, output)
    assert isinstance(result, ParsingResult)
    assert result.success_count == 2
    assert result.failure_count == 1
    assert [item.value for item in result.successes] == ["first", "second"]

    failure = result.failures[0]
    assert failure.raw_text == "invalid line"
    assert failure.line_number == 2
    assert failure.attempted_patterns


def test_engine_parses_iterable_output_and_handles_validation_error() -> None:
    lines: Iterable[str] = ["count: 10", "count: not-a-number"]
    result = parse_output(IntResponse, lines)

    assert result.success_count == 1
    assert result.failure_count == 1
    assert result.successes[0].count == 10

    failure = result.failures[0]
    assert "not-a-number" in failure.raw_text
    assert failure.exception is not None


def test_engine_skips_empty_lines_without_failures() -> None:
    output = "value: first\n\nvalue: second"
    result = parse_output(SimpleResponse, output)
    assert result.success_count == 2
    assert result.failure_count == 0
