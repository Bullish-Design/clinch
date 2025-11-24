# src/clinch/exceptions.py
from __future__ import annotations

from typing import Sequence

from clinch.parsing import ParsingFailure


class CLInchException(Exception):
    """Base exception for all CLInch-specific errors."""


class ParsingError(CLInchException):
    """Raised when parsing fails in strict mode."""

    def __init__(self, failures: Sequence[ParsingFailure]) -> None:
        """Initialize with a sequence of failures and build a message.

        The first failure is used to build a short preview in the
        error message, truncated to 200 characters.
        """
        # Preserve the original sequence object; tests assert identity.
        self.failures = failures
        count = len(failures)

        prefix = f"Failed to parse {count} line(s)"
        if failures:
            first = failures[0]
            text = first.raw_text
            if len(text) > 200:
                text = text[:200] + "..."
            preview = f"(line {first.line_number}: {text})"
            # Include an explicit "First failure" phrase for tests.
            suffix = f" {preview} First failure: {text}"
        else:
            suffix = ""

        super().__init__(prefix + suffix)


class CommandNotFoundError(CLInchException):
    """Raised when the underlying command cannot be found."""


class TimeoutError(CLInchException):
    """Raised when a command exceeds the configured timeout."""
