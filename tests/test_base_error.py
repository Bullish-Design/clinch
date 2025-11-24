# tests/test_base_error.py
from __future__ import annotations

from clinch import BaseCLIError, Field


def test_base_cli_error_creation_all_fields() -> None:
    error = BaseCLIError(
        exit_code=1,
        stderr="something went wrong",
        stdout="partial output",
        command="cmd --flag",
    )
    assert error.exit_code == 1
    assert error.stderr == "something went wrong"
    assert error.stdout == "partial output"
    assert error.command == "cmd --flag"


def test_base_cli_error_minimal_fields_use_default_stdout() -> None:
    error = BaseCLIError(
        exit_code=2,
        stderr="fail",
        command="cmd",
    )
    assert error.exit_code == 2
    assert error.stderr == "fail"
    assert error.command == "cmd"
    assert error.stdout == ""


def test_base_cli_error_str_includes_command_exit_code_and_stderr() -> None:
    error = BaseCLIError(exit_code=3, stderr="boom", command="mycmd")
    message = str(error)
    assert "mycmd" in message
    assert "3" in message
    assert "boom" in message


def test_base_cli_error_str_truncates_long_stderr() -> None:
    long_stderr = "x" * 250
    error = BaseCLIError(exit_code=1, stderr=long_stderr, command="cmd")
    message = str(error)

    # Extract the stderr preview part after the prefix
    prefix = "Command 'cmd' failed with exit code 1: "
    assert message.startswith(prefix)
    preview = message[len(prefix):]

    # Should be first 200 chars plus ellipsis
    assert preview.startswith(long_stderr[:200])
    assert preview.endswith("...")
    assert len(preview) == 200 + 3


def test_base_cli_error_as_exception() -> None:
    error = BaseCLIError(exit_code=1, stderr="fail", command="cmd")

    try:
        raise error
    except BaseCLIError as exc:
        assert exc.exit_code == 1
        assert exc.stderr == "fail"


def test_custom_error_parsing_success() -> None:
    class CustomError(BaseCLIError):
        error_code: str = Field(pattern=r"ERR-(\d+)")

    error = CustomError.parse_from_stderr(
        stderr="ERR-404: not found",
        exit_code=1,
        command="cmd",
    )

    assert isinstance(error, CustomError)
    assert error.exit_code == 1
    assert error.command == "cmd"
    assert error.stderr == "ERR-404: not found"
    assert error.error_code == "404"


def test_custom_error_parsing_fallback_on_no_match() -> None:
    class CustomError(BaseCLIError):
        error_code: str = Field(pattern=r"ERR-(\d+)")

    stderr = "no error code here"
    error = CustomError.parse_from_stderr(
        stderr=stderr,
        exit_code=2,
        command="cmd",
        stdout="some stdout",
    )

    assert isinstance(error, CustomError)
    assert error.exit_code == 2
    assert error.command == "cmd"
    assert error.stdout == "some stdout"
    assert error.stderr == stderr
