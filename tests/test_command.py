# tests/test_command.py
from __future__ import annotations

import pytest
from pydantic import ValidationError, field_validator

from clinch import Field
from clinch.base import BaseCLICommand, BaseCLIResponse, CLIWrapper


class _TestResponse(BaseCLIResponse):
    value: str = Field(pattern=r"value: (\w+)")


class SimpleCommand(BaseCLICommand):
    subcommand = "test"
    response_model = _TestResponse


class ParameterizedCommand(BaseCLICommand):
    subcommand = "test"
    response_model = _TestResponse

    verbose: bool = False
    count: int = 10

    @field_validator("count")
    @classmethod
    def validate_count(cls, v: int) -> int:
        if v < 1:
            raise ValueError("count must be positive")
        return v

    def build_args(self) -> list[str]:
        args = [self.subcommand]
        if self.verbose:
            args.append("--verbose")
        args.extend(["--count", str(self.count)])
        return args


def test_simple_command() -> None:
    """Test basic command creation."""
    cmd = SimpleCommand()
    assert cmd.build_args() == ["test"]
    assert cmd.get_response_model() == _TestResponse


def test_parameterized_command() -> None:
    """Test command with parameters."""
    cmd = ParameterizedCommand(verbose=True, count=5)
    assert cmd.build_args() == ["test", "--verbose", "--count", "5"]


def test_command_validation() -> None:
    """Test command parameter validation."""
    with pytest.raises(ValidationError):
        ParameterizedCommand(count=-1)


def test_execute_command(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test wrapper.execute_command()."""

    class EchoCommand(BaseCLICommand):
        subcommand = "value: hello"
        response_model = _TestResponse

    class TestWrapper(CLIWrapper):
        command = "echo"

    # Patch _execute to avoid shelling out
    def fake_execute(self: TestWrapper, *args: str, response_model: type[TestResponse]):
        output = args[0]
        return response_model.parse_output(output)

    monkeypatch.setattr(TestWrapper, "_execute", fake_execute)

    wrapper = TestWrapper()
    cmd = EchoCommand()
    result = wrapper.execute_command(cmd)
    assert result.success_count == 1
    assert result.successes[0].value == "hello"
