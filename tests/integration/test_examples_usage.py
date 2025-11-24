# tests/integration/test_examples_usage.py
from __future__ import annotations

from clinch.examples import EchoWrapper, LsWrapper


def test_echo_wrapper_example_round_trip() -> None:
    wrapper = EchoWrapper()
    result = wrapper.echo_value("example")
    assert result.value == "example"


def test_ls_wrapper_example_lists_entries() -> None:
    wrapper = LsWrapper()
    entries = wrapper.list_entries()
    assert isinstance(entries, list)
    assert len(entries) >= 1
