# src/clinch/parsing/engine.py
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Type, TypeVar, cast

from pydantic import BaseModel, ValidationError

from clinch.parsing import ParsingFailure, ParsingResult

TModel = TypeVar("TModel", bound=BaseModel)


def _normalize_output(output: str | Iterable[str]) -> List[str]:
    if isinstance(output, str):
        return output.splitlines()
    return list(output)


def parse_output(
    model: Type[TModel],
    output: str | Iterable[str],
) -> ParsingResult[TModel]:
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
            match = re.search(pattern, raw_line)
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
            result.failures.append(
                ParsingFailure(
                    raw_text=raw_line,
                    attempted_patterns=list(attempted_patterns),
                    exception=str(exc),
                    line_number=index,
                )
            )
            continue

        result.successes.append(instance)

    return result
