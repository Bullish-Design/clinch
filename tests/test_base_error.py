# tests/test_base_error.py
from __future__ import annotations

from clinch import BaseCLIError, Field


def test_base_cli_error_can_be_instantiated_and_str() -> None:
    error = BaseCLIError(exit_code=1, stderr="oops", stdout="", command="cmd")
    assert error.exit_code == 1
    assert "cmd" in str(error)
    assert "oops" in str(error)


def test_base_cli_error_truncates_long_stderr_in_str() -> None:
    long_stderr = "x" * 500
    error = BaseCLIError(exit_code=1, stderr=long_stderr, stdout="", command="cmd")
    message = str(error)
    assert "..." in message
    assert "cmd" in message


def test_error_subclass_with_pattern_parses_from_stderr() -> None:
    class CustomError(BaseCLIError):
        error_code = Field(pattern=r"ERR-(\d+)")

    stderr = "ERR-404: not found"
    error = CustomError.parse_from_stderr(
        stderr=stderr,
        exit_code=2,
        command="cmd",
        stdout="",
    )

    assert isinstance(error, CustomError)
    assert error.exit_code == 2
    assert error.command == "cmd"
    assert error.error_code == "404"


def test_parse_from_stderr_handles_no_match_gracefully() -> None:
    class CustomError(BaseCLIError):
        error_code = Field(pattern=r"ERR-(\d+)")

    stderr = "no error code here"
    error = CustomError.parse_from_stderr(
        stderr=stderr,
        exit_code=3,
        command="cmd",
        stdout="out",
    )

    assert isinstance(error, CustomError)
    assert error.exit_code == 3
    assert error.stderr == stderr
    # No attribute error_code should be present when parsing fails
    assert not hasattr(error, "error_code")
