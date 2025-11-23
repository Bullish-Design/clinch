# tests/test_base_response.py
from __future__ import annotations

from typing import Iterable

from clinch import BaseCLIResponse, Field
from clinch.parsing import ParsingResult


class _TestResponse(BaseCLIResponse):
    value: str = Field(pattern=r"value: (\w+)")


def test_base_cli_response_is_pydantic_model() -> None:
    instance = _TestResponse(value="ok")
    assert isinstance(instance, BaseCLIResponse)
    assert instance.value == "ok"


def test_parse_output_placeholder_with_string_returns_empty_result() -> None:
    output = "value: test\nvalue: other"
    result = _TestResponse.parse_output(output)
    assert isinstance(result, ParsingResult)
    assert result.success_count == 0
    assert result.failure_count == 0
    assert result.successes == []
    assert result.failures == []


def test_parse_output_placeholder_with_iterable_returns_empty_result() -> None:
    lines: Iterable[str] = ["value: one", "value: two"]
    result = _TestResponse.parse_output(lines)
    assert isinstance(result, ParsingResult)
    assert result.success_count == 0
    assert result.failure_count == 0


def test_base_cli_response_has_field_patterns_mapping() -> None:
    assert hasattr(_TestResponse, "_field_patterns")
    assert isinstance(_TestResponse._field_patterns, dict)
    assert _TestResponse._field_patterns == {}
