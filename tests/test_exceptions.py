# tests/test_exceptions.py
from __future__ import annotations

from clinch.exceptions import (
    CLInchException,
    CommandNotFoundError,
    ParsingError,
    TimeoutError,
)
from clinch.parsing import ParsingFailure


def _make_failure(line: str = "bad line", line_number: int = 1) -> ParsingFailure:
    return ParsingFailure(
        raw_text=line,
        attempted_patterns=[r"(\w+)"],
        exception=None,
        line_number=line_number,
    )


def test_clinch_exception_can_be_raised_and_caught() -> None:
    try:
        raise CLInchException("boom")
    except CLInchException as exc:
        assert str(exc) == "boom"


def test_parsing_error_with_single_failure() -> None:
    failures = [_make_failure("line", 1)]
    error = ParsingError(failures)

    assert error.failures is failures
    assert "Failed to parse 1 line(s)" in str(error)
    assert "First failure: line" in str(error)


def test_parsing_error_with_multiple_failures() -> None:
    failures = [
        _make_failure("first line", 1),
        _make_failure("second line", 2),
    ]
    error = ParsingError(failures)

    assert error.failures is failures
    assert "Failed to parse 2 line(s)" in str(error)


def test_parsing_error_message_truncates_long_line() -> None:
    long_text = "this is a very long line that should be truncated in error message"
    failures = [
        _make_failure(long_text, 1),
    ]
    error = ParsingError(failures)
    message = str(error)

    assert "Failed to parse 1 line(s)" in message
    assert "this is a very long line that should be trunca" in message


def test_exception_hierarchy() -> None:
    error = ParsingError([])
    assert isinstance(error, CLInchException)
    assert isinstance(error, Exception)


def test_command_not_found_error_creation() -> None:
    error = CommandNotFoundError("mytool not found")
    assert isinstance(error, CLInchException)
    assert isinstance(error, Exception)
    assert "mytool not found" in str(error)


def test_timeout_error_creation() -> None:
    error = TimeoutError("timed out")
    assert isinstance(error, CLInchException)
    assert isinstance(error, Exception)
    assert "timed out" in str(error)
