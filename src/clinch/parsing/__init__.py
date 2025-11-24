# src/clinch/parsing/__init__.py
from __future__ import annotations

from .engine import parse_output
from .result import ParsingFailure, ParsingResult

__all__ = ["parse_output", "ParsingFailure", "ParsingResult"]
