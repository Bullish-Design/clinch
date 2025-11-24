# tests/integration/test_examples.py
from __future__ import annotations

from clinch import Field
from clinch.base import BaseCLIResponse, CLIWrapper


class EchoExampleResponse(BaseCLIResponse):
    value: str = Field(pattern=r"value=(\w+)")


class EchoExampleWrapper(CLIWrapper):
    command = "echo"
    strict_mode: bool = True

    def echo_value(self, value: str) -> EchoExampleResponse:
        result = self._execute(f"value={value}", response_model=EchoExampleResponse)
        return result.successes[0]


class LsExampleResponse(BaseCLIResponse):
    entry: str = Field(pattern=r"(.+)")


class LsExampleWrapper(CLIWrapper):
    command = "ls"

    def list_entries(self, *paths: str) -> list[str]:
        result = self._execute(*paths, response_model=LsExampleResponse)
        return [item.entry for item in result.successes]


def test_echo_example_wrapper_round_trip() -> None:
    wrapper = EchoExampleWrapper()
    result = wrapper.echo_value("example")
    assert result.value == "example"


def test_ls_example_wrapper_lists_entries() -> None:
    wrapper = LsExampleWrapper()
    entries = wrapper.list_entries()
    assert isinstance(entries, list)
    assert len(entries) >= 1
