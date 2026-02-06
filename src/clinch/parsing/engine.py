# src/clinch/parsing/engine.py
from __future__ import annotations

import re
from collections.abc import Iterable
from functools import lru_cache
from typing import Any, TypeVar, cast

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


def get_cache_info() -> dict[str, int]:
    """Return basic statistics about the compiled pattern cache."""
    info = _compile_pattern.cache_info()
    return {
        "hits": info.hits,
        "misses": info.misses,
        "size": info.currsize,
        "maxsize": info.maxsize,
    }


def _normalize_output(output: str | Iterable[str]) -> list[str]:
    """Normalize CLI output into a list of lines."""
    if isinstance(output, str):
        return output.splitlines()
    return list(output)


def _extract_match_values(
    match: re.Match[str],
    field_name: str,
) -> dict[str, Any]:
    """Extract values from a regex match.

    Supports three modes:
    - Named groups: ``(?P<name>...)`` maps directly to field names.
    - Single capture group: maps to the given field_name.
    - No capture group: full match maps to the given field_name.

    When named groups are present, they take priority.  This allows a
    single pattern to populate multiple model fields at once.
    """
    named = {k: v for k, v in match.groupdict().items() if v is not None}
    if named:
        return named

    if match.groups():
        return {field_name: match.group(1)}

    return {field_name: match.group(0)}


def parse_output(  # noqa: UP047
    model: type[TModel],
    output: str | Iterable[str],
) -> ParsingResult[TModel]:
    """Parse CLI output into instances of the given response model."""
    lines = _normalize_output(output)
    result: ParsingResult[TModel] = ParsingResult()

    patterns = cast(dict[str, str], getattr(model, "_field_patterns", {}) or {})

    for index, raw_line in enumerate(lines, start=1):
        if not raw_line.strip():
            continue

        matched_values: dict[str, Any] = {}
        attempted_patterns: list[str] = []

        for field_name, pattern in patterns.items():
            attempted_patterns.append(pattern)
            compiled_pattern = _compile_pattern(pattern)
            match = compiled_pattern.search(raw_line)
            if not match:
                continue

            extracted = _extract_match_values(match, field_name)
            matched_values.update(extracted)

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


def parse_blocks(  # noqa: UP047
    model: type[TModel],
    output: str | Iterable[str],
    *,
    delimiter: str = "",
) -> ParsingResult[TModel]:
    """Parse multi-line record blocks from CLI output.

    Records are separated by lines matching *delimiter* (empty string
    means blank lines).  Within each block, every line is matched against
    all field patterns and the extracted values are merged into a single
    model instance.

    This is useful for CLI tools that produce multi-line records such as
    ``git log``, ``apt show``, ``ip addr``, etc.
    """
    lines = _normalize_output(output)
    result: ParsingResult[TModel] = ParsingResult()
    patterns = cast(dict[str, str], getattr(model, "_field_patterns", {}) or {})

    blocks: list[list[tuple[int, str]]] = []
    current_block: list[tuple[int, str]] = []

    for index, raw_line in enumerate(lines, start=1):
        is_delimiter = raw_line.strip() == delimiter if delimiter else not raw_line.strip()
        if is_delimiter:
            if current_block:
                blocks.append(current_block)
                current_block = []
        else:
            current_block.append((index, raw_line))

    if current_block:
        blocks.append(current_block)

    for block in blocks:
        matched_values: dict[str, Any] = {}
        attempted_patterns: list[str] = []
        first_line_number = block[0][0]
        raw_block_text = "\n".join(line for _, line in block)

        for _, raw_line in block:
            for field_name, pattern in patterns.items():
                attempted_patterns.append(pattern)
                compiled_pattern = _compile_pattern(pattern)
                match = compiled_pattern.search(raw_line)
                if not match:
                    continue
                extracted = _extract_match_values(match, field_name)
                matched_values.update(extracted)

        if not matched_values:
            result.failures.append(
                ParsingFailure(
                    raw_text=raw_block_text,
                    attempted_patterns=list(attempted_patterns),
                    exception=None,
                    line_number=first_line_number,
                )
            )
            continue

        try:
            instance = model(**matched_values)
        except ValidationError as exc:
            try:
                exception_detail = exc.json()
            except Exception:
                exception_detail = str(exc)

            result.failures.append(
                ParsingFailure(
                    raw_text=raw_block_text,
                    attempted_patterns=list(attempted_patterns),
                    exception=exception_detail,
                    line_number=first_line_number,
                )
            )
            continue

        result.successes.append(instance)

    return result
