# tests/test_parsing_engine.py
from __future__ import annotations

from typing import Iterable

from pydantic import BaseModel, ValidationError, field_validator

from clinch import BaseCLIResponse, Field
from clinch.parsing import ParsingResult
from clinch.parsing.engine import (
    _compile_pattern,
    clear_pattern_cache,
    get_cache_info,
    parse_output,
)


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


def test_pattern_caching_returns_same_compiled_object() -> None:
    pattern = r"test: (\w+)"
    compiled_first = _compile_pattern(pattern)
    compiled_second = _compile_pattern(pattern)
    assert compiled_first is compiled_second


def test_cache_clearing_resets_cache_size() -> None:
    clear_pattern_cache()
    _compile_pattern(r"test: (\w+)")
    info_before = get_cache_info()
    assert info_before["size"] > 0

    clear_pattern_cache()
    info_after = get_cache_info()
    assert info_after["size"] == 0


def test_validation_error_details_preserved_as_json() -> None:
    class StrictModel(BaseCLIResponse):
        value: int = Field(pattern=r"value: (-?\d+)")

        @field_validator("value")
        @classmethod
        def value_positive(cls, v: int) -> int:
            if v < 0:
                raise ValueError("must be positive")
            return v

    StrictModel._field_patterns = {"value": r"value: (-?\d+)"}

    result = parse_output(StrictModel, "value: -5")

    assert result.failure_count == 1
    failure = result.failures[0]
    assert failure.exception is not None
    assert "positive" in failure.exception.lower()
