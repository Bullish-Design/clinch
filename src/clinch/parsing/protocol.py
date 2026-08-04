"""Parser protocol — the pluggable parsing strategy contract.

All parsers (the built-in regex engine, the optional jc adapter, and any
user-supplied custom parser) conform to the :class:`Parser` protocol.

The protocol is intentionally minimal: a single ``parse`` method that
accepts the full CLI output as a string and returns a :class:`ParserOutput`
with raw dict records and any parser-level failures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from clinch.parsing.result import ParsingFailure


@dataclass
class ParserOutput:
    """Container returned by every :class:`Parser` implementation.

    This is the *raw* output of a parser — a list of dicts (one per
    logical record) plus any failures the parser itself detected (e.g.
    lines that didn't match any regex pattern).  The parsing engine
    takes this structure and constructs Pydantic model instances from
    the ``records``, adding validation errors as additional failures.
    """

    records: list[dict[str, Any]] = field(default_factory=list)
    failures: list[ParsingFailure] = field(default_factory=list)


@runtime_checkable
class Parser(Protocol):
    """Protocol for pluggable CLI output parsers.

    A parser accepts the raw stdout/stderr of a command (single string)
    and returns structured data ready for Pydantic model construction.

    Implementations
    ---------------
    * :class:`~clinch.parsing.regex_parser.RegexParser` — the default,
      line-by-line regex extraction engine.
    * :class:`~clinch.parsing.jc_parser.JCParser` — optional adapter
      delegating to `jc <https://github.com/kellyjonbrazil/jc>`_.

    Custom parsers
    --------------
    Any callable or object conforming to this protocol can be used::

        from clinch.parsing import Parser, ParserOutput

        class MyCustomParser:
            def parse(self, output: str) -> ParserOutput:
                records = [{"key": line} for line in output.splitlines() if line]
                return ParserOutput(records=records)

        class MyResponse(BaseCLIResponse):
            _cli_parser = MyCustomParser()
            key: str
    """

    def parse(self, output: str) -> ParserOutput:
        """Parse raw CLI output into structured records.

        Parameters
        ----------
        output:
            The full stdout (or stderr) of a command as a single string,
            including embedded newlines.

        Returns
        -------
        ParserOutput
            Structured records and any parser-level failures.
        """
        ...
