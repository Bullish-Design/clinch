# src/clinch/exceptions.py
from __future__ import annotations

"""Exception hierarchy for CLInch.

These exceptions are used throughout the library to provide structured
error handling for parsing and CLI execution.
"""

from clinch.parsing.result import ParsingFailure


class CLInchException(Exception):
    """Base exception for all CLInch errors."""


class ParsingError(CLInchException):
    """Raised when parsing fails in strict mode.

    Carries the collection of :class:`ParsingFailure` instances that
    triggered the error. The string representation includes a short
    summary and a preview of the first failing line.
    """

    def __init__(self, failures: list[ParsingFailure]) -> None:
        self.failures = failures
        super().__init__(self.__str__())

    def __str__(self) -> str:
        if not self.failures:
            return "Failed to parse 0 line(s)."

        first = self.failures[0]
        preview = first.raw_text[:50]
        return f"Failed to parse {len(self.failures)} line(s). First failure: {preview}..."


class CommandNotFoundError(CLInchException):
    """Raised when CLI command doesn't exist in PATH."""


class TimeoutError(CLInchException):
    """Raised when CLI command execution exceeds timeout."""
