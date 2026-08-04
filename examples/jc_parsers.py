# examples/jc_parsers.py
"""Dropping jc's parser catalog into CLInch response models.

Requires the optional extra: ``pip install clinch[jc]``

This example uses jc's ``csv`` parser — deterministic, no external
tools needed — but any of jc's 170+ parsers (``ps``, ``dig``, ``df``,
``ifconfig``, ``netstat``, ...) can be bound the same way via the
pluggable ``Parser`` layer.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from clinch import BaseCLIResponse, CLIWrapper
from clinch.parsing import JCParser, ParsingResult, parse_output


class CsvRow(BaseCLIResponse):
    """One row of a CSV file, parsed by jc's ``csv`` parser.

    jc returns every value as a string; Pydantic coerces and validates
    (``age: int`` turns ``"42"`` into ``42``).
    """

    _cli_parser = JCParser("csv")

    name: str
    age: int


class CsvWrapper(CLIWrapper):
    """Wrapper around ``cat`` for reading CSV files."""

    command = "cat"

    def read(self, path: Path) -> ParsingResult[CsvRow]:
        return self._execute(str(path), response_model=CsvRow)


def main() -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as fh:
        fh.write("name,age\nfoo,42\nbar,7\n")
        path = Path(fh.name)

    # Path 1: through a wrapper (cat sample.csv -> jc csv -> CsvRow)
    wrapper = CsvWrapper()
    result = wrapper.read(path)
    for row in result.successes:
        print(f"{row.name} is {row.age} (age type: {type(row.age).__name__})")

    # Path 2: drive the parser directly, no wrapper involved
    raw = "name,age\nbaz,99\n"
    direct = parse_output(CsvRow, raw, parser=JCParser("csv"))
    print("direct:", [(row.name, row.age) for row in direct.successes])

    path.unlink()


if __name__ == "__main__":
    main()
