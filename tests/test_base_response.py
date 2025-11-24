# tests/test_base_response.py
from __future__ import annotations

from clinch import Field
from clinch.base import BaseCLIResponse
from clinch.parsing import ParsingResult


class ParentResponse(BaseCLIResponse):
    parent_field: str = Field(pattern=r"parent: (\w+)")


class ChildResponse(ParentResponse):
    child_field: str = Field(pattern=r"child: (\w+)")


class Response1(BaseCLIResponse):
    field1: str = Field(pattern=r"field1: (\w+)")


class Response2(BaseCLIResponse):
    field2: str = Field(pattern=r"field2: (\w+)")


def test_base_response_field_patterns_for_base_and_subclasses() -> None:
    assert dict(BaseCLIResponse._field_patterns) == {}
    assert dict(Response1._field_patterns) == {"field1": r"field1: (\w+)"}
    assert dict(Response2._field_patterns) == {"field2": r"field2: (\w+)"}
    assert dict(ParentResponse._field_patterns) == {"parent_field": r"parent: (\w+)"}
    assert dict(ChildResponse._field_patterns) == {
        "parent_field": r"parent: (\w+)",
        "child_field": r"child: (\w+)",
    }


class SimpleResponse(BaseCLIResponse):
    value: str = Field(pattern=r"value: (\w+)")


def test_parse_output_uses_patterns_and_returns_parsing_result() -> None:
    output = "value: test\nno match"
    result = SimpleResponse.parse_output(output)
    assert isinstance(result, ParsingResult)
    assert result.success_count == 1
    assert result.failure_count == 1
    assert result.successes[0].value == "test"
