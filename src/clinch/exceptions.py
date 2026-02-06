# src/clinch/exceptions.py
from __future__ import annotations

"""Exception hierarchy for CLInch."""

from clinch.parsing.result import ParsingFailure  # noqa: E402


class CLInchException(Exception):  # noqa: N818
    """Base exception for all CLInch errors."""


class ParsingError(CLInchException):
    """Raised when parsing fails in strict mode."""

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


class CommandTimeoutError(CLInchException):
    """Raised when CLI command execution exceeds timeout."""


# Backward-compatible alias (deprecated, prefer CommandTimeoutError)
TimeoutError = CommandTimeoutError  # noqa: A001
