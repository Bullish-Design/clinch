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


class PsProcess(BaseCLIResponse):
    """One process row from ``ps -eo pid,comm,rss``, parsed by jc's ``ps`` parser."""

    _cli_parser = JCParser("ps")

    pid: int
    command: str
    rss: int  # resident set size, KB


class PsWrapper(CLIWrapper):
    """Wrapper around ``ps`` using jc's battle-tested parser."""

    command = "ps"

    def processes(self) -> ParsingResult[PsProcess]:
        return self._execute("-eo", "pid,comm,rss", response_model=PsProcess)


class DfUsage(BaseCLIResponse):
    """One filesystem row from ``df -h``, parsed by jc's ``df`` parser.

    jc normalizes the human-readable columns back to bytes.
    """

    _cli_parser = JCParser("df")

    filesystem: str
    size: int
    used: int
    available: int
    use_percent: int
    mounted_on: str


class DfWrapper(CLIWrapper):
    """Wrapper around ``df`` using jc's battle-tested parser."""

    command = "df"

    def usage(self) -> ParsingResult[DfUsage]:
        return self._execute("-h", response_model=DfUsage)


def _top_processes() -> None:
    wrapper = PsWrapper()
    result = wrapper.processes()
    print(f"parsed {result.success_count} processes, {result.failure_count} failures")
    top = sorted(result.successes, key=lambda p: p.rss, reverse=True)[:5]
    for proc in top:
        print(f"  pid {proc.pid:>6}  {proc.rss / 1024:>8.1f} MB  {proc.command}")


def _filesystem_usage() -> None:
    wrapper = DfWrapper()
    result = wrapper.usage()
    print(f"parsed {result.success_count} filesystems, {result.failure_count} failures")
    for fs in result.successes:
        print(f"  {fs.filesystem} mounted on {fs.mounted_on}: {fs.use_percent}% used")


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

    # Real tools through jc's parser catalog
    _top_processes()
    _filesystem_usage()


if __name__ == "__main__":
    main()
