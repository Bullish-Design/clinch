# tests/test_wrapper.py
from __future__ import annotations

from clinch import BaseCLIError
from clinch.base import BaseCLIResponse, CLIWrapper
from clinch.fields import Field


class DummyResponse(BaseCLIResponse):
    value: str = Field(pattern=r"value: (\w+)")


class DefaultWrapper(CLIWrapper):
    command = "dummy"


class StrictWrapper(CLIWrapper):
    command = "dummy"
    strict_mode: bool = True  # <-- add annotation here


def test_default_wrapper_configuration() -> None:
    wrapper = DefaultWrapper()
    assert wrapper.command == "dummy"
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
    # Positional arguments preserved at the front
    assert args[0:2] == ["pos1", "pos2"]

    # True bool becomes a flag, False/None are omitted
    assert "--flag" in args
    assert "--skip" not in args
    assert "--optional" not in args

    # Non-bool keyword becomes --key value
    assert "--count" in args
    count_index = args.index("--count")
    assert args[count_index + 1] == "3"


def test_preprocess_output_is_noop_by_default() -> None:
    wrapper = DefaultWrapper()
    text = "some output"
    assert wrapper._preprocess_output(text) == text
