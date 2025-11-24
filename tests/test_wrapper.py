# tests/test_wrapper.py
from __future__ import annotations

from typing import Any

import pytest

from clinch import BaseCLIError, CommandNotFoundError, ParsingError, TimeoutError
from clinch.base import BaseCLIResponse, CLIWrapper
from clinch.fields import Field


class DummyResponse(BaseCLIResponse):
    value: str = Field(pattern=r"value: (\w+)")


class EchoWrapper(CLIWrapper):
    command = "echo"


class StrictEchoWrapper(CLIWrapper):
    command = "echo"
    strict_mode: bool = True


class MissingWrapper(CLIWrapper):
    command = "definitely-missing-command-xyz123"


class FailWrapper(CLIWrapper):
    command = "ls"


class _TestWrapper(CLIWrapper):
    command = "tool"


def test_default_wrapper_configuration() -> None:
    wrapper = EchoWrapper()
    assert wrapper.command == "echo"
    assert wrapper.strict_mode is False
    assert wrapper.timeout == 30
    assert wrapper._get_error_model() is BaseCLIError


def test_strict_wrapper_overrides_strict_mode_and_preserves_timeout_default() -> None:
    wrapper = StrictEchoWrapper()
    assert wrapper.strict_mode is True
    assert wrapper.timeout == 30


def test_build_args_none_values() -> None:
    wrapper = _TestWrapper()
    args = wrapper._build_args(present="value", absent=None)
    assert args == ["--present", "value"]


def test_build_args_list_values() -> None:
    wrapper = _TestWrapper()
    args = wrapper._build_args(exclude=["a", "b", "c"])
    assert args == ["--exclude", "a", "--exclude", "b", "--exclude", "c"]


def test_build_args_numeric() -> None:
    wrapper = _TestWrapper()
    args = wrapper._build_args(count=42, ratio=3.14)
    assert args == ["--count", "42", "--ratio", "3.14"]


def test_build_positional_args() -> None:
    wrapper = _TestWrapper()
    args = wrapper._build_positional_args("one", 2, 3.5)
    assert args == ["one", "2", "3.5"]


def test_preprocess_output_is_noop_by_default() -> None:
    wrapper = EchoWrapper()
    text = "some output"
    assert wrapper._preprocess_output(text) == text


def test_custom_build_args() -> None:
    class CustomWrapper(CLIWrapper):
        command = "tool"

        def _build_args(self, **kwargs: Any) -> list[str]:
            return [f"-{k[0]}" for k, v in kwargs.items() if v]

    wrapper = CustomWrapper()
    args = wrapper._build_args(verbose=True, quiet=True)
    assert args == ["-v", "-q"]


def test_execute_success_parses_output() -> None:
    wrapper = EchoWrapper()
    result = wrapper._execute("value: hello", response_model=DummyResponse)

    assert result.success_count == 1
    assert result.failure_count == 0
    assert result.successes[0].value == "hello"


def test_execute_with_positional_args() -> None:
    class TestResponse(BaseCLIResponse):
        output: str = Field(pattern=r"(.+)")

    wrapper = EchoWrapper()
    result = wrapper._execute("test", "arg1", "arg2", response_model=TestResponse)
    assert result.success_count == 1


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


def test_strict_mode_raises_on_parsing_failure() -> None:
    class PartialResponse(BaseCLIResponse):
        value: str = Field(pattern=r"value: (\w+)")

    class StrictWrapper(CLIWrapper):
        command = "echo"
        strict_mode: bool = True

    wrapper = StrictWrapper()

    with pytest.raises(ParsingError) as exc_info:
        wrapper._execute("invalid line", response_model=PartialResponse)

    error = exc_info.value
    assert error.failures
    assert error.failures[0].raw_text == "invalid line"


def test_permissive_mode_returns_result_with_failures() -> None:
    class PartialResponse(BaseCLIResponse):
        value: str = Field(pattern=r"value: (\w+)")

    class PermissiveWrapper(CLIWrapper):
        command = "echo"
        strict_mode: bool = False

    wrapper = PermissiveWrapper()
    result = wrapper._execute("invalid line", response_model=PartialResponse)

    from clinch.parsing import ParsingResult

    assert isinstance(result, ParsingResult)
    assert result.failure_count == 1
    assert result.success_count == 0


def test_timeout_raises_timeout_error() -> None:
    class EmptyResponse(BaseCLIResponse):
        pass

    class SleepWrapper(CLIWrapper):
        command = "sleep"
        timeout: int = 1

    wrapper = SleepWrapper()

    with pytest.raises(TimeoutError):
        wrapper._execute("2", response_model=EmptyResponse)


def test_preprocess_output_is_used_for_parsing() -> None:
    class PreprocessedResponse(BaseCLIResponse):
        value: str = Field(pattern=r"VALUE: (\w+)")

    class PreprocessingWrapper(CLIWrapper):
        command = "echo"

        def _preprocess_output(self, output: str) -> str:
            return output.upper()

    wrapper = PreprocessingWrapper()
    result = wrapper._execute("value: test", response_model=PreprocessedResponse)

    assert result.success_count == 1
    assert result.failure_count == 0
    assert result.successes[0].value == "TEST"

def test_timeout_validation() -> None:
    """CLIWrapper.timeout must be positive and not too large."""
    from pydantic import ValidationError

    class BadTimeoutWrapper(CLIWrapper):
        command = "echo"
        timeout: int = 0

    with pytest.raises(ValidationError, match="timeout must be positive"):
        BadTimeoutWrapper()

    class TooLargeTimeoutWrapper(CLIWrapper):
        command = "echo"
        timeout: int = 10000

    with pytest.raises(ValidationError, match="must not exceed 600 seconds"):
        TooLargeTimeoutWrapper()


def test_command_required() -> None:
    """Wrapper must define command class variable."""
    class NoCommandWrapper(CLIWrapper):
        pass

    with pytest.raises(TypeError, match="must define 'command'"):
        NoCommandWrapper()


def test_command_defined_works() -> None:
    """Wrapper with command should instantiate successfully."""
    class ValidWrapper(CLIWrapper):
        command = "echo"

    wrapper = ValidWrapper()
    assert wrapper.command == "echo"
