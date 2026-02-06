# tests/test_parsing_engine.py
from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, field_validator

from clinch import BaseCLIResponse, Field
from clinch.parsing import ParsingResult
from clinch.parsing.engine import (
    _compile_pattern,
    clear_pattern_cache,
    get_cache_info,
    parse_blocks,
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


# --- Named group tests (#1) ---

class NamedGroupResponse(BaseCLIResponse):
    pid: str = Field(pattern=r"(?P<pid>\d+)\s+(?P<name>\S+)")
    name: str = Field(default="")


def test_named_groups_populate_multiple_fields() -> None:
    """Named capture groups map directly to model field names."""
    output = "1234 nginx\n5678 postgres"
    result = parse_output(NamedGroupResponse, output)

    assert result.success_count == 2
    assert result.successes[0].pid == "1234"
    assert result.successes[0].name == "nginx"
    assert result.successes[1].pid == "5678"
    assert result.successes[1].name == "postgres"


# --- Block parsing tests (#2) ---

class GitCommitBlock(BaseCLIResponse):
    commit_hash: str = Field(pattern=r"commit (\w+)")
    author: str = Field(pattern=r"Author: (.+)")
    message: str = Field(pattern=r"    (.+)")


def test_parse_blocks_separates_by_blank_lines() -> None:
    output = """commit abc123
Author: Alice
    First commit

commit def456
Author: Bob
    Second commit"""

    result = parse_blocks(GitCommitBlock, output)
    assert result.success_count == 2
    assert result.successes[0].commit_hash == "abc123"
    assert result.successes[0].author == "Alice"
    assert result.successes[0].message == "First commit"
    assert result.successes[1].commit_hash == "def456"
    assert result.successes[1].author == "Bob"
    assert result.successes[1].message == "Second commit"


def test_parse_blocks_with_custom_delimiter() -> None:
    output = "name: Alice\nage: 30\n---\nname: Bob\nage: 25"

    class PersonBlock(BaseCLIResponse):
        name: str = Field(pattern=r"name: (\w+)")
        age: str = Field(pattern=r"age: (\d+)")

    result = parse_blocks(PersonBlock, output, delimiter="---")
    assert result.success_count == 2
    assert result.successes[0].name == "Alice"
    assert result.successes[0].age == "30"
    assert result.successes[1].name == "Bob"
    assert result.successes[1].age == "25"


def test_parse_blocks_failure_on_no_match() -> None:
    output = "no patterns here\n\nalso nothing"
    result = parse_blocks(EngineResponse, output)
    assert result.success_count == 0
    assert result.failure_count == 2


def test_parse_blocks_via_response_model() -> None:
    """BaseCLIResponse.parse_blocks delegates to engine."""
    output = "commit abc123\nAuthor: Alice\n    Hello\n\ncommit def456\nAuthor: Bob\n    World"
    result = GitCommitBlock.parse_blocks(output)
    assert result.success_count == 2
