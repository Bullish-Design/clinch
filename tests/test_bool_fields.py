# tests/test_bool_fields.py
"""Pattern-presence semantics for bool-typed fields.

The regex engine extracts raw text; for a ``bool`` field the engine
applies marker semantics before Pydantic validation:

* captured text Pydantic can coerce (``yes``/``no``/``1``/``0``/...) is
  passed through unchanged;
* any other captured marker (e.g. ``*`` for ``git branch``) means the
  pattern matched, i.e. ``True``;
* a non-matching pattern leaves the field absent so its default applies.
"""

from __future__ import annotations

from clinch import BaseCLIResponse, Field
from clinch.parsing import ParserOutput, parse_output


class MarkerResponse(BaseCLIResponse):
    name: str = Field(pattern=r"\*?\s+(\S+)")
    is_current: bool = Field(default=False, pattern=r"(\*)")


def test_marker_capture_means_true() -> None:
    result = parse_output(MarkerResponse, "* main\n")
    assert result.failure_count == 0
    assert result.successes[0].is_current is True


def test_missing_marker_uses_default() -> None:
    result = parse_output(MarkerResponse, "  origin/feature\n")
    assert result.failure_count == 0
    assert result.successes[0].is_current is False


class LiteralResponse(BaseCLIResponse):
    enabled: bool = Field(default=False, pattern=r"state=(yes|no)")
    numeric: bool = Field(default=False, pattern=r"flag=(\d)")


def test_coercible_literals_pass_through() -> None:
    result = parse_output(
        LiteralResponse,
        "state=yes flag=1\nstate=no flag=0\n",
    )
    assert result.failure_count == 0
    assert [r.enabled for r in result.successes] == [True, False]
    assert [r.numeric for r in result.successes] == [True, False]


class NonLiteralMarker(BaseCLIResponse):
    is_up: bool = Field(default=False, pattern=r"status=(up|down)")


def test_non_coercible_capture_means_true() -> None:
    """A bool field's pattern is a predicate: matched means True.

    ``(up|down)`` matches both values, so both lines are True — faithful
    execution of a declaration that matches both.  To mean "up only",
    write the pattern as the predicate (see
    ``test_bool_pattern_as_predicate``).
    """
    result = parse_output(NonLiteralMarker, "status=up\nstatus=down\n")
    assert result.failure_count == 0
    assert [r.is_up for r in result.successes] == [True, True]


class PredicateResponse(BaseCLIResponse):
    """The honest way to derive a bool from a value-bearing line."""

    status: str = Field(pattern=r"status=(\w+)")  # keep the value
    is_up: bool = Field(default=False, pattern=r"status=up")  # the predicate


def test_bool_pattern_as_predicate() -> None:
    """Write the pattern as the predicate to get per-value truth."""
    result = parse_output(PredicateResponse, "status=up\nstatus=down\n")
    assert result.failure_count == 0
    assert [(r.status, r.is_up) for r in result.successes] == [("up", True), ("down", False)]


class OptionalMarker(BaseCLIResponse):
    name: str = Field(pattern=r"server (\w+)")
    active: bool | None = Field(default=None, pattern=r"(ACTIVE)")


def test_optional_bool_marker() -> None:
    result = parse_output(OptionalMarker, "server ACTIVE\nserver idle\n")
    assert result.failure_count == 0
    assert result.successes[0].active is True
    assert result.successes[1].active is None


class NoCaptureGroup(BaseCLIResponse):
    name: str = Field(pattern=r"\*?\s*(\S+)")
    starred: bool = Field(default=False, pattern=r"\*")


def test_pattern_without_capture_group() -> None:
    result = parse_output(NoCaptureGroup, "* item\nitem\n")
    assert result.failure_count == 0
    assert result.successes[0].starred is True
    assert result.successes[1].starred is False


class _BoolRecordParser:
    """Custom parser that already returns native bools."""

    def parse(self, output: str) -> ParserOutput:
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        records = [{"name": line, "is_current": line.startswith("*")} for line in lines]
        return ParserOutput(records=records)


class ParserBoolResponse(BaseCLIResponse):
    _cli_parser = _BoolRecordParser()

    name: str
    is_current: bool


def test_native_bools_from_parser_pass_through() -> None:
    result = parse_output(ParserBoolResponse, "* main\n  other\n", parser=_BoolRecordParser())
    assert result.failure_count == 0
    assert [r.is_current for r in result.successes] == [True, False]
