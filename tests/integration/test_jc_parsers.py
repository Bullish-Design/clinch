# tests/integration/test_jc_parsers.py
"""Integration tests for the optional jc parser adapter.

These tests exercise the real ``jc`` library and are skipped when it is
not installed (``pip install clinch[jc]``).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

jc = pytest.importorskip("jc")

from clinch import BaseCLIResponse, CLIWrapper  # noqa: E402
from clinch.parsing import JCParser, parse_output  # noqa: E402


class CsvRow(BaseCLIResponse):
    _cli_parser = JCParser("csv")

    name: str
    age: int


class CsvWrapper(CLIWrapper):
    command = "cat"

    def read(self, path: Path):
        return self._execute(str(path), response_model=CsvRow)


def _csv_file() -> Path:
    fh = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False)
    fh.write("name,age\nfoo,42\nbar,7\n")
    fh.close()
    return Path(fh.name)


def test_jc_parser_through_wrapper() -> None:
    path = _csv_file()
    try:
        result = CsvWrapper().read(path)
    finally:
        path.unlink()

    assert [row.name for row in result.successes] == ["foo", "bar"]
    assert all(isinstance(row.age, int) for row in result.successes)
    assert not result.has_failures


def test_jc_parser_direct_with_explicit_parser() -> None:
    raw = "name,age\nbaz,99\n"
    result = parse_output(CsvRow, raw, parser=JCParser("csv"))
    assert result.success_count == 1
    assert result.successes[0].name == "baz"
    assert result.successes[0].age == 99


def test_jc_parser_validation_error_becomes_failure() -> None:
    # age is non-numeric: jc returns "old" as a string, Pydantic rejects it
    raw = "name,age\nfoo,old\n"
    result = parse_output(CsvRow, raw, parser=JCParser("csv"))
    assert result.success_count == 0
    assert result.failure_count == 1
