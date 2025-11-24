# tests/test_wrapper.py
from __future__ import annotations

import pytest

from clinch import BaseCLIError, CommandNotFoundError
from clinch.base import BaseCLIResponse, CLIWrapper
from clinch.fields import Field


class DummyResponse(BaseCLIResponse):
    value: str = Field(pattern=r"value: (\w+)")


class DefaultWrapper(CLIWrapper):
    command = "echo"


class StrictWrapper(CLIWrapper):
    command = "echo"
    strict_mode: bool = True


class MissingWrapper(CLIWrapper):
    command = "definitely-missing-command-xyz123"


class FailWrapper(CLIWrapper):
    command = "ls"


def test_default_wrapper_configuration() -> None:
    wrapper = DefaultWrapper()
    assert wrapper.command == "echo"
    assert wrapper.strict_mode is False
    assert wrapper.timeout == 30
    assert wrapper._get_error_model() is BaseCLIError


def test_strict_wrapper_overrides_strict_mode_and_preserves_timeout_default() -> None:
    wrapper = StrictWrapper()
    assert wrapper.strict_mode is True
    assert wrapper.timeout == 30


def test_build_args_includes_positional_and_keyword_arguments() -> None:
    wrapper = DefaultWrapper()
    args = wrapper._build_args("pos1", "pos2", flag=True, count=3, skip=False, optional=None)

    assert isinstance(args, list)
    assert args[0:2] == ["pos1", "pos2"]
    assert "--flag" in args
    assert "--skip" not in args
    assert "--optional" not in args
    assert "--count" in args
    count_index = args.index("--count")
    assert args[count_index + 1] == "3"


def test_preprocess_output_is_noop_by_default() -> None:
    wrapper = DefaultWrapper()
    text = "some output"
    assert wrapper._preprocess_output(text) == text


def test_execute_success_parses_output() -> None:
    wrapper = DefaultWrapper()
    result = wrapper._execute("value: hello", response_model=DummyResponse)

    assert result.success_count == 1
    assert result.failure_count == 0
    assert result.successes[0].value == "hello"


def test_execute_command_not_found_raises_command_not_found_error() -> None:
    wrapper = MissingWrapper()
    with pytest.raises(CommandNotFoundError):
        wrapper._execute("value: test", response_model=DummyResponse)


def test_execute_non_zero_exit_raises_error_model() -> None:
    wrapper = FailWrapper()
    with pytest.raises(BaseCLIError) as exc_info:
        wrapper._execute("/nonexistent/path/xyz", response_model=DummyResponse)

    assert exc_info.value.exit_code != 0
    assert "ls" in exc_info.value.command
