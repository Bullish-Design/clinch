"""Default regex-based parser extracted from the core parsing engine.

This module wraps the existing per-field regex extraction logic into
the :class:`Parser` protocol so it can be swapped out or composed with
other parser backends.
"""

from __future__ import annotations

import re
from functools import lru_cache

from clinch.parsing.protocol import ParserOutput
from clinch.parsing.result import ParsingFailure


@lru_cache(maxsize=256)
def _compile(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern)


class RegexParser:
    """Line-by-line regex extraction parser.

    This is the **default parser** used when a :class:`BaseCLIResponse`
    subclass does not set ``_cli_parser``.  Each line of output is tested
    against every pattern declared via :func:`~clinch.Field`.  Lines that
    match at least one pattern produce a record; lines that match nothing
    produce a :class:`~clinch.ParsingFailure`.

    Parameters
    ----------
    patterns:
        Mapping of field name → regex pattern string, typically sourced
        from ``BaseCLIResponse._field_patterns``.
    """

    def __init__(self, patterns: dict[str, str]) -> None:
        self._patterns = patterns

    def parse(self, output: str) -> ParserOutput:
        """Parse CLI output line-by-line using the stored regex patterns."""
        lines = output.splitlines()
        records: list[dict[str, object]] = []
        failures: list[ParsingFailure] = []

        for index, raw_line in enumerate(lines, start=1):
            if not raw_line.strip():
                continue

            matched_values: dict[str, object] = {}
            attempted_patterns: list[str] = list(self._patterns.values())

            for field_name, pattern in self._patterns.items():
                compiled = _compile(pattern)
                match = compiled.search(raw_line)
                if not match:
                    continue
                value: object = match.group(1) if match.groups() else match.group(0)
                matched_values[field_name] = value

            if not matched_values:
                failures.append(
                    ParsingFailure(
                        raw_text=raw_line,
                        attempted_patterns=attempted_patterns,
                        exception=None,
                        line_number=index,
                    )
                )
                continue

            records.append(matched_values)

        return ParserOutput(records=records, failures=failures)
