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


def test_simple_command() -> None:
    """Test basic command creation."""
    cmd = SimpleCommand()
    assert cmd.build_args() == ["test"]
    assert cmd.get_response_model() == _TestResponse


def test_parameterized_command_auto_build_args() -> None:
    """Test auto build_args converts fields to flags."""
    cmd = ParameterizedCommand(verbose=True, count=5)
    args = cmd.build_args()
    assert "test" in args
    assert "--verbose" in args
    assert "--count" in args
    assert "5" in args


def test_parameterized_command_auto_skips_false_bool() -> None:
    """False booleans are omitted from auto build_args."""
    cmd = ParameterizedCommand(verbose=False, count=10)
    args = cmd.build_args()
    assert "--verbose" not in args
    assert "--count" in args


def test_command_auto_build_args_with_none() -> None:
    """None values are skipped in auto build_args."""

    class NullableCommand(BaseCLICommand):
        subcommand = "run"
        response_model = _TestResponse
        path: str | None = None

    cmd = NullableCommand()
    assert cmd.build_args() == ["run"]

    cmd2 = NullableCommand(path="/tmp")
    args = cmd2.build_args()
    assert "--path" in args
    assert "/tmp" in args


def test_command_auto_build_args_with_list() -> None:
    """List values are expanded in auto build_args."""

    class ListCommand(BaseCLICommand):
        subcommand = "search"
        response_model = _TestResponse
        tags: list[str] = []

    cmd = ListCommand(tags=["a", "b"])
    args = cmd.build_args()
    assert args.count("--tags") == 2
    assert "a" in args
    assert "b" in args


def test_command_auto_build_args_underscore_to_hyphen() -> None:
    """Underscores in field names become hyphens in flags."""

    class HyphenCommand(BaseCLICommand):
        subcommand = "deploy"
        response_model = _TestResponse
        dry_run: bool = True

    cmd = HyphenCommand()
    args = cmd.build_args()
    assert "--dry-run" in args


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
    def fake_execute(self: TestWrapper, *args: str, response_model: type, **kwargs: object):  # type: ignore[override]
        output = args[0]
        return response_model.parse_output(output)

    monkeypatch.setattr(TestWrapper, "_execute", fake_execute)

    wrapper = TestWrapper()
    cmd = EchoCommand()
    result = wrapper.execute_command(cmd)
    assert result.success_count == 1
    assert result.successes[0].value == "hello"
