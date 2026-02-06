# src/clinch/__init__.py
from __future__ import annotations

"""CLInch public API.

This module exposes the main entry points for users of the library:
custom fields, parsing results, core base classes, and the exception
hierarchy.
"""

from .base import BaseCLICommand, BaseCLIError, BaseCLIResponse, CLIWrapper  # noqa: E402
from .exceptions import (  # noqa: E402
    CLInchException,
    CommandNotFoundError,
    CommandTimeoutError,
    ParsingError,
    TimeoutError,  # noqa: A004
)
from .fields import Field  # noqa: E402
from .parsing import ParsingFailure, ParsingResult  # noqa: E402
from .utils import regex_helpers  # noqa: E402

__all__ = [
    "Field",
    "ParsingFailure",
    "ParsingResult",
    "CLInchException",
    "ParsingError",
    "CommandNotFoundError",
    "CommandTimeoutError",
    "TimeoutError",
    "regex_helpers",
    "BaseCLIResponse",
    "BaseCLIError",
    "CLIWrapper",
    "BaseCLICommand",
]

__version__ = "0.2.0"
