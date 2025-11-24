# src/clinch/parsing/engine.py
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Type, TypeVar, cast

from pydantic import BaseModel, ValidationError

from clinch.parsing import ParsingFailure, ParsingResult

TModel = TypeVar("TModel", bound=BaseModel)


@lru_cache(maxsize=256)
def _compile_pattern(pattern: str) -> re.Pattern[str]:
    """Compile and cache regex patterns used by the parsing engine."""
    return re.compile(pattern)


def clear_pattern_cache() -> None:
    """Clear the compiled regex pattern cache."""
    _compile_pattern.cache_clear()


def get_cache_info() -> Dict[str, int]:
    """Return basic statistics about the compiled pattern cache."""
    info = _compile_pattern.cache_info()
    return {
        "hits": info.hits,
        "misses": info.misses,
        "size": info.currsize,
        "maxsize": info.maxsize,
    }


def _normalize_output(output: str | Iterable[str]) -> List[str]:
    """Normalize CLI output into a list of lines."""
    if isinstance(output, str):
        return output.splitlines()
    return list(output)


def parse_output(
    model: Type[TModel],
    output: str | Iterable[str],
) -> ParsingResult[TModel]:
    """Parse CLI output into instances of the given response model."""
    lines = _normalize_output(output)
    result: ParsingResult[TModel] = ParsingResult()

    patterns = cast(Dict[str, str], getattr(model, "_field_patterns", {}) or {})

    for index, raw_line in enumerate(lines, start=1):
        if not raw_line.strip():
            continue

        matched_values: Dict[str, Any] = {}
        attempted_patterns: List[str] = []

        for field_name, pattern in patterns.items():
            attempted_patterns.append(pattern)
            compiled_pattern = _compile_pattern(pattern)
            match = compiled_pattern.search(raw_line)
            if not match:
                continue

            if match.groups():
                value: Any = match.group(1)
            else:
                value = match.group(0)

            matched_values[field_name] = value

        if not matched_values:
            result.failures.append(
                ParsingFailure(
                    raw_text=raw_line,
                    attempted_patterns=list(attempted_patterns),
                    exception=None,
                    line_number=index,
                )
            )
            continue

        try:
            instance = model(**matched_values)
        except ValidationError as exc:
            # Preserve full validation details where possible
            try:
                exception_detail = exc.json()
            except Exception:
                exception_detail = str(exc)

            result.failures.append(
                ParsingFailure(
                    raw_text=raw_line,
                    attempted_patterns=list(attempted_patterns),
                    exception=exception_detail,
                    line_number=index,
                )
            )
            continue

        result.successes.append(instance)

    return result
