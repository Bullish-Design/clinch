# tests/test_base_response.py
from __future__ import annotations

from typing import Iterable

from clinch import BaseCLIResponse, Field
from clinch.parsing import ParsingResult


class _TestResponse(BaseCLIResponse):
    value: str = Field(pattern=r"value: (\w+)")

    # def __init__(self, value: str) -> None:  # pragma: no cover
    #     super().__init__(value=value)


class MixedResponse(BaseCLIResponse):
    with_pattern: str = Field(pattern=r"pattern: (\w+)")
    without_pattern: str
    default_only: str = Field(default="x")


class ParentResponse(BaseCLIResponse):
    parent_field: str = Field(pattern=r"parent: (\w+)")


class ChildResponse(ParentResponse):
    child_field: str = Field(pattern=r"child: (\w+)")


def test_base_cli_response_is_pydantic_model() -> None:
    instance = _TestResponse(value="ok")
    assert isinstance(instance, BaseCLIResponse)
    assert instance.value == "ok"


def test_parse_output_parses_successful_lines() -> None:
    output = "value: first\nvalue: second"
    result = _TestResponse.parse_output(output)
    assert isinstance(result, ParsingResult)
    assert result.success_count == 2
    assert result.failure_count == 0
    assert [item.value for item in result.successes] == ["first", "second"]


def test_parse_output_tracks_failures_for_non_matching_lines() -> None:
    output = "value: first\nnot a match"
    result = _TestResponse.parse_output(output)
    assert result.success_count == 1
    assert result.failure_count == 1
    assert result.successes[0].value == "first"
    failure = result.failures[0]
    assert failure.raw_text == "not a match"
    assert failure.line_number == 2
    assert failure.attempted_patterns


def test_parse_output_accepts_iterable_output() -> None:
    lines: Iterable[str] = ["value: one", "value: two"]
    result = _TestResponse.parse_output(lines)
    assert result.success_count == 2
    assert [item.value for item in result.successes] == ["one", "two"]


def test_extract_field_patterns_picks_up_only_pattern_fields() -> None:
    patterns = MixedResponse._extract_field_patterns()
    assert patterns == {"with_pattern": r"pattern: (\w+)"}  # no entry for fields without pattern


def test_field_patterns_populated_on_subclass_creation() -> None:
    assert _TestResponse._field_patterns == {"value": r"value: (\w+)"}


def test_field_patterns_are_inherited_and_merged() -> None:
    assert ParentResponse._field_patterns["parent_field"] == r"parent: (\w+)"
    assert ChildResponse._field_patterns["parent_field"] == r"parent: (\w+)"
    assert ChildResponse._field_patterns["child_field"] == r"child: (\w+)"
