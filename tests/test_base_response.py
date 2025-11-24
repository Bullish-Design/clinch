# tests/test_base_response.py
from __future__ import annotations

from typing import Iterable, Mapping

from clinch import BaseCLIResponse, Field
from clinch.parsing import ParsingResult


class TestResponse(BaseCLIResponse):
    value: str = Field(pattern=r"value: (\w+)")


class MixedResponse(BaseCLIResponse):
    with_pattern: str = Field(pattern=r"pattern: (\w+)")
    without_pattern: str
    default_only: str = Field(default="x")


class ParentResponse(BaseCLIResponse):
    parent_field: str = Field(pattern=r"parent: (\w+)")


class ChildResponse(ParentResponse):
    child_field: str = Field(pattern=r"child: (\w+)")


class Response1(BaseCLIResponse):
    field1: str = Field(pattern=r"field1: (\w+)")


class Response2(BaseCLIResponse):
    field2: str = Field(pattern=r"field2: (\w+)")


def test_base_cli_response_is_pydantic_model() -> None:
    instance = TestResponse(value="ok")
    assert isinstance(instance, BaseCLIResponse)
    assert instance.value == "ok"


def test_parse_output_parses_successful_lines() -> None:
    output = "value: first\nvalue: second"
    result = TestResponse.parse_output(output)
    assert isinstance(result, ParsingResult)
    assert result.success_count == 2
    assert result.failure_count == 0
    assert [item.value for item in result.successes] == ["first", "second"]


def test_parse_output_tracks_failures_for_non_matching_lines() -> None:
    output = "value: first\nnot a match"
    result = TestResponse.parse_output(output)
    assert result.success_count == 1
    assert result.failure_count == 1
    assert result.successes[0].value == "first"
    failure = result.failures[0]
    assert failure.raw_text == "not a match"
    assert failure.line_number == 2
    assert failure.attempted_patterns


def test_parse_output_accepts_iterable_output() -> None:
    lines: Iterable[str] = ["value: one", "value: two"]
    result = TestResponse.parse_output(lines)
    assert result.success_count == 2
    assert [item.value for item in result.successes] == ["one", "two"]


def test_extract_field_patterns_picks_up_only_pattern_fields() -> None:
    patterns = MixedResponse._extract_field_patterns()
    assert patterns == {"with_pattern": r"pattern: (\w+)"}  # no entry for fields without pattern


def test_field_patterns_populated_on_subclass_access() -> None:
    patterns: Mapping[str, str] = TestResponse._field_patterns
    assert dict(patterns) == {"value": r"value: (\w+)"}  # lazily computed


def test_field_patterns_do_not_leak_between_unrelated_subclasses() -> None:
    patterns1 = dict(Response1._field_patterns)
    patterns2 = dict(Response2._field_patterns)
    assert patterns1 == {"field1": r"field1: (\w+)"}
    assert patterns2 == {"field2": r"field2: (\w+)"}
    assert patterns1 is not patterns2
    assert patterns1 != patterns2


def test_field_patterns_are_inherited_and_extended_in_subclasses() -> None:
    assert dict(ParentResponse._field_patterns) == {"parent_field": r"parent: (\w+)"}
    assert dict(ChildResponse._field_patterns) == {
        "parent_field": r"parent: (\w+)",
        "child_field": r"child: (\w+)",
    }


def test_base_cli_response_class_has_empty_field_patterns() -> None:
    patterns: Mapping[str, str] = BaseCLIResponse._field_patterns
    assert dict(patterns) == {}
