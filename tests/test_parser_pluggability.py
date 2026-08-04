"""Tests for the pluggable parser architecture."""

from __future__ import annotations

from pydantic import BaseModel

from clinch import BaseCLIResponse, Field
from clinch.parsing import Parser, ParserOutput, RegexParser
from clinch.parsing.engine import parse_output

# ---------------------------------------------------------------------------
# Custom parser
# ---------------------------------------------------------------------------

class _UpperParser:
    """Trivial custom parser that returns one record per line, uppercased."""

    def parse(self, output: str) -> ParserOutput:
        records = [{"value": line.upper()} for line in output.splitlines() if line.strip()]
        return ParserOutput(records=records)


class UpperModel(BaseCLIResponse):
    _cli_parser = _UpperParser()
    value: str


class ExplicitModel(BaseModel):
    value: str


# ---------------------------------------------------------------------------
# Parser that raises
# ---------------------------------------------------------------------------

class _ExplodingParser:
    def parse(self, output: str) -> ParserOutput:
        raise RuntimeError("boom")


class ExplodingModel(BaseCLIResponse):
    _cli_parser = _ExplodingParser()
    value: str


# ---------------------------------------------------------------------------
# Parser that returns a record that fails validation
# ---------------------------------------------------------------------------

class _BadRecordParser:
    def parse(self, output: str) -> ParserOutput:
        return ParserOutput(records=[{"value": object()}])


class ValidateModel(BaseCLIResponse):
    _cli_parser = _BadRecordParser()
    value: str


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_custom_parser_via_cli_parser_classvar() -> None:
    """_cli_parser on the response model is used by parse_output."""
    result = UpperModel.parse_output("hello\nworld\n")
    assert result.success_count == 2
    assert result.successes[0].value == "HELLO"
    assert result.successes[1].value == "WORLD"


def test_custom_parser_via_explicit_parameter() -> None:
    """An explicit parser= parameter overrides _cli_parser."""
    result = parse_output(ExplicitModel, "a\nb\nc", parser=_UpperParser())
    assert result.success_count == 3
    assert [r.value for r in result.successes] == ["A", "B", "C"]


def test_parser_exception_produces_failure() -> None:
    """When a parser raises, a single ParsingFailure is returned."""
    result = ExplodingModel.parse_output("anything")
    assert result.success_count == 0
    assert result.failure_count == 1
    assert "boom" in result.failures[0].exception


def test_validation_error_after_parser_is_reported() -> None:
    """Records that fail Pydantic validation appear as failures."""
    result = ValidateModel.parse_output("anything")
    assert result.success_count == 0
    assert result.failure_count == 1
    assert result.failures[0].exception is not None


def test_regex_parser_conforms_to_protocol() -> None:
    """RegexParser satisfies the Parser protocol."""
    rp = RegexParser({"key": r"(\S+)"})
    assert isinstance(rp, Parser)


def test_protocol_rejects_non_conformant() -> None:
    """Objects without .parse() are not valid Parsers."""

    class NotAParser:
        pass

    assert not isinstance(NotAParser(), Parser)


def test_parser_output_defaults() -> None:
    """ParserOutput defaults to empty lists."""
    po = ParserOutput()
    assert po.records == []
    assert po.failures == []


def test_regex_parser_failure_includes_line_number() -> None:
    """RegexParser reports the correct line number for non-matching lines."""
    rp = RegexParser({"value": r"^ok: (\w+)"})
    out = rp.parse("ok: yes\nbad line\nok: no")
    assert len(out.records) == 2
    assert len(out.failures) == 1
    assert out.failures[0].line_number == 2
    assert out.failures[0].raw_text == "bad line"


def test_regex_parser_empty_output() -> None:
    """Empty string produces no records, no failures."""
    out = RegexParser({"x": r"(.+)"}).parse("")
    assert out.records == []
    assert out.failures == []


def test_explicit_parser_overrides_field_patterns() -> None:
    """When an explicit parser is provided, field patterns are ignored."""

    class NameUpperParser:
        def parse(self, output: str) -> ParserOutput:
            return ParserOutput(records=[{"name": output.strip().upper()}])

    class PatternModel(BaseCLIResponse):
        name: str = Field(pattern=r"name: (.+)")

    result = parse_output(PatternModel, "anything", parser=NameUpperParser())
    assert result.success_count == 1
    assert result.successes[0].name == "ANYTHING"
