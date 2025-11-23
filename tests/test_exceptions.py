# tests/test_exceptions.py
from __future__ import annotations

from typing import List

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
        attempted_patterns=["pattern1"],
        exception="boom",
        line_number=line_number,
    )


def test_parsing_error_stores_failures_and_builds_message() -> None:
    failures: List[ParsingFailure] = [
        _make_failure("one", 1),
        _make_failure("two", 2),
    ]

    error = ParsingError(failures)

    assert isinstance(error, CLInchException)
    assert isinstance(error, Exception)
    assert error.failures == failures
    assert error.failure_count == 2
    assert "2 parsing failure" in str(error)


def test_command_not_found_error_includes_command_and_original_exception() -> None:
    original = FileNotFoundError("No such file or directory")
    error = CommandNotFoundError(command="mytool", original_exception=original)

    assert isinstance(error, CLInchException)
    assert isinstance(error, Exception)
    assert error.command == "mytool"
    assert error.original_exception is original
    # Message should contain both the command and underlying message
    message = str(error)
    assert "mytool" in message
    assert "No such file or directory" in message


def test_timeout_error_includes_command_and_timeout() -> None:
    error = TimeoutError(command="sleep", timeout=1.5)

    assert isinstance(error, CLInchException)
    assert isinstance(error, Exception)
    assert error.command == "sleep"
    assert error.timeout == 1.5
    message = str(error)
    assert "sleep" in message
    assert "1.5" in message


def test_exception_hierarchy() -> None:
    error = ParsingError([])
    assert isinstance(error, CLInchException)
    assert isinstance(error, Exception)
