# src/clinch/parsing/engine.py
from __future__ import annotations

import re
from typing import Dict, Iterable, Mapping, TypeVar

from pydantic import BaseModel

from .result import ParsingFailure, ParsingResult

TModel = TypeVar("TModel", bound=BaseModel)


def parse_output(
    model: type[TModel],
    output: str | Iterable[str],
) -> ParsingResult[TModel]:
    if isinstance(output, str):
        lines = output.splitlines()
    else:
        lines = list(output)

    patterns: Mapping[str, str] = getattr(model, "_field_patterns", {})  # type: ignore[attr-defined]
    pattern_items = list(patterns.items())
    attempted_patterns_all = [p for _, p in pattern_items]

    successes: list[TModel] = []
    failures: list[ParsingFailure] = []

    for idx, line in enumerate(lines, start=1):
        # Skip completely empty/whitespace-only lines without creating failures
        if not line.strip():
            continue

        data: Dict[str, str] = {}
        matched_any = False

        for field_name, pattern in pattern_items:
            match = re.search(pattern, line)
            if not match:
                continue
            matched_any = True
            if match.groups():
                data[field_name] = match.group(1)
            else:
                data[field_name] = match.group(0)

        if matched_any:
            try:
                instance = model.model_validate(data)
            except Exception as exc:
                failures.append(
                    ParsingFailure(
                        raw_text=line,
                        line_number=idx,
                        attempted_patterns=list(attempted_patterns_all),
                        exception=exc,
                        message=str(exc),
                    )
                )
            else:
                successes.append(instance)
        else:
            failures.append(
                ParsingFailure(
                    raw_text=line,
                    line_number=idx,
                    attempted_patterns=list(attempted_patterns_all),
                    message="No patterns matched",
                )
            )

    return ParsingResult[TModel](successes=successes, failures=failures)
