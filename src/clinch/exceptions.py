# src/clinch/exceptions.py
from __future__ import annotations

from typing import Iterable

from clinch.parsing import ParsingFailure


class CLInchException(Exception):
    """Base exception for all CLInch errors."""


class ParsingError(CLInchException):
    """Raised when parsing fails in strict mode.

    Carries the collection of :class:`ParsingFailure` instances that
    triggered the error so callers can inspect which lines failed and why.
    """

    def __init__(self, failures: Iterable[ParsingFailure]) -> None:
        self.failures = list(failures)
        message = f"{len(self.failures)} parsing failure(s)"
        super().__init__(message)

    @property
    def failure_count(self) -> int:
        """Number of parsing failures associated with this error."""
        return len(self.failures)


class CommandNotFoundError(CLInchException):
    """Raised when the configured CLI command cannot be found."""

    def __init__(
        self,
        command: str,
        original_exception: Exception | None = None,
    ) -> None:
        self.command = command
        self.original_exception = original_exception

        base_message = f"Command not found: {command}"
        if original_exception is not None:
            base_message = f"{base_message} ({original_exception})"

        super().__init__(base_message)


class TimeoutError(CLInchException):
    """Raised when command execution times out."""

    def __init__(self, command: str, timeout: float) -> None:
        self.command = command
        self.timeout = float(timeout)
        message = f"Command '{command}' timed out after {self.timeout} seconds"
        super().__init__(message)
