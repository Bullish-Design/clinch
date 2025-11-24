# src/clinch/__init__.py
from __future__ import annotations

"""CLInch public API."""

from .base import BaseCLIError, BaseCLIResponse, CLIWrapper
from .exceptions import CLInchException, CommandNotFoundError, ParsingError, TimeoutError
from .fields import Field
from .parsing import ParsingFailure, ParsingResult
from .utils import regex_helpers

__all__ = [
    "Field",
    "ParsingFailure",
    "ParsingResult",
    "CLInchException",
    "ParsingError",
    "CommandNotFoundError",
    "TimeoutError",
    "regex_helpers",
    "BaseCLIResponse",
    "BaseCLIError",
    "CLIWrapper",
]
