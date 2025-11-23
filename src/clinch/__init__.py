# src/clinch/__init__.py
from __future__ import annotations

"""CLInch public API.

This module re-exports the most commonly used pieces of the library,
including the custom :func:`Field`, parsing result types, exceptions, and
the :mod:`clinch.utils.regex_helpers` module for common regex patterns.
"""

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
]
