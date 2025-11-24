# tests/test_parsing_engine.py
from __future__ import annotations

from typing import Iterable

from pydantic import BaseModel

from clinch import BaseCLIResponse, Field
from clinch.parsing.engine import parse_output
from clinch.parsing import ParsingResult


class EngineResponse(BaseCLIResponse):
    value: str = Field(pattern=r"value: (\w+)")


class PlainModel(BaseModel):
    value: str


def test_parse_output_with_response_model() -> None:
    output = "value: one\nvalue: two"
    result = parse_output(EngineResponse, output)
    assert isinstance(result, ParsingResult)
    assert result.success_count == 2
    assert [item.value for item in result.successes] == ["one", "two"]


def test_parse_output_with_iterable_lines() -> None:
    lines: Iterable[str] = ["value: x", "value: y"]
    result = parse_output(EngineResponse, lines)
    assert result.success_count == 2


def test_parse_output_records_failures_for_non_matching_lines() -> None:
    output = "value: ok\nno match here"
    result = parse_output(EngineResponse, output)
    assert result.success_count == 1
    assert result.failure_count == 1
    failure = result.failures[0]
    assert failure.raw_text == "no match here"
    assert failure.line_number == 2
