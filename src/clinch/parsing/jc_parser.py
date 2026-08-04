"""Optional jc parser adapter.

Wraps `jc <https://github.com/kellyjonbrazil/jc>`_ as a :class:`Parser`
so that any of jc's 170+ built-in parsers can be dropped into a
:class:`BaseCLIResponse` subclass without writing imperative parsing code.

Usage
-----
::

    from clinch import BaseCLIResponse, CLIWrapper
    from clinch.parsing import JCParser

    class DigAnswer(BaseCLIResponse):
        _cli_parser = JCParser("dig")

        name: str
        ttl: int
        data: str

Installation
------------
jc is an **optional** dependency.  Install with::

    pip install clinch[jc]
"""

from __future__ import annotations

from typing import Any

from clinch.parsing.protocol import ParserOutput


class JCParser:
    """Adapter that delegates parsing to jc.

    Parameters
    ----------
    parser_name:
        The jc parser name (e.g. ``"dig"``, ``"ps"``, ``"ifconfig"``).
        See `jc parser plugins <https://github.com/kellyjonbrazil/jc/blob/master/docs/parser_plugins.md>`_
        for the full catalogue.
    **kwargs:
        Forwarded to :func:`jc.parse` as keyword arguments (e.g.
        ``quiet=True`` to suppress warnings).
    """

    def __init__(self, parser_name: str, **kwargs: Any) -> None:
        self._parser_name = parser_name
        self._kwargs = kwargs

    def parse(self, output: str) -> ParserOutput:
        """Parse CLI output by delegating to jc."""
        try:
            import jc
        except ImportError:
            raise ImportError(
                "jc is required for JCParser.  Install with:\n"
                "    pip install clinch[jc]"
            ) from None

        result = jc.parse(self._parser_name, output, **self._kwargs)

        if isinstance(result, list):
            records = result
        elif isinstance(result, dict):
            records = [result]
        else:
            records = []

        return ParserOutput(records=records)
