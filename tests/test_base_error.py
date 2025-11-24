# tests/test_base_error.py
from __future__ import annotations

from clinch import BaseCLIError, Field


def test_base_cli_error_creation_and_str() -> None:
    error = BaseCLIError(
        exit_code=1,
        stderr="command failed",
        stdout="",
        command="test command",
    )

    assert error.exit_code == 1
    assert error.stderr == "command failed"
    assert error.stdout == ""
    assert error.command == "test command"

    assert (
        str(error)
        == "Command 'test command' failed with exit code 1: command failed"
    )


def test_base_cli_error_truncates_long_stderr() -> None:
    long_stderr = "x" * 300
    error = BaseCLIError(
        exit_code=1,
        stderr=long_stderr,
        stdout="",
        command="cmd",
    )

    message = str(error)
    # Ensure it's truncated with "..."
    assert "..." in message
    assert "x" * 200 in message


def test_base_cli_error_is_exception() -> None:
    error = BaseCLIError(
        exit_code=2,
        stderr="boom",
        stdout="",
        command="run cmd",
    )

    try:
        raise error
    except BaseCLIError as caught:
        assert caught is error


class NotFoundError(BaseCLIError):
    error_code: str = Field(pattern=r"code: (\d+)")


def test_parse_from_stderr_with_matching_pattern() -> None:
    stderr = "something went wrong\ncode: 404 not found\nmore text"
    error = NotFoundError.parse_from_stderr(
        stderr=stderr,
        exit_code=1,
        command="curl http://example.com/missing",
        stdout="",
    )

    assert isinstance(error, NotFoundError)
    assert error.exit_code == 1
    assert error.command.startswith("curl")
    assert error.error_code == "404"


def test_parse_from_stderr_with_no_match_falls_back() -> None:
    stderr = "no structured code here"
    error = NotFoundError.parse_from_stderr(
        stderr=stderr,
        exit_code=3,
        command="curl http://example.com/other",
        stdout="",
    )

    assert isinstance(error, NotFoundError)
    assert error.exit_code == 3
    assert error.stderr == stderr
    # error_code should not be populated when pattern doesn't match
    assert not hasattr(error, "unknown_field")
