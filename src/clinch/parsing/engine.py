"""Parsing engine — orchestrates parser → Pydantic model construction.

This module is the bridge between raw parser output and validated
Pydantic model instances.  It accepts an optional :class:`Parser`
implementation (defaulting to :class:`RegexParser` with the model's
``_field_patterns``) and handles model construction, validation-error
tracking, and :class:`ParsingResult` assembly.
"""

from __future__ import annotations

from typing import Any, Iterable, Type, TypeVar, cast

from pydantic import BaseModel, ValidationError

from clinch.parsing.protocol import Parser, ParserOutput
from clinch.parsing.regex_parser import RegexParser, _compile
from clinch.parsing.result import ParsingFailure, ParsingResult

TModel = TypeVar("TModel", bound=BaseModel)


def clear_pattern_cache() -> None:
    """Clear the compiled regex pattern cache."""
    _compile.cache_clear()  # type: ignore[attr-defined]


def get_cache_info() -> dict[str, int]:
    """Return basic statistics about the compiled pattern cache."""
    info = _compile.cache_info()  # type: ignore[attr-defined]
    return {
        "hits": info.hits,
        "misses": info.misses,
        "size": info.currsize,
        "maxsize": info.maxsize,
    }


def _normalize_to_str(output: str | Iterable[str]) -> str:
    """Normalize CLI output into a single string."""
    if isinstance(output, str):
        return output
    return "\n".join(output)


def parse_output(
    model: Type[TModel],
    output: str | Iterable[str],
    parser: Parser | None = None,
) -> ParsingResult[TModel]:
    """Parse CLI output into validated instances of *model*.

    Parameters
    ----------
    model:
        A :class:`BaseCLIResponse` (or any :class:`pydantic.BaseModel`)
        subclass whose field names correspond to the keys produced by
        *parser*.
    output:
        Raw CLI stdout/stderr — either a single string or an iterable
        of lines.
    parser:
        An optional :class:`Parser` implementation.  When ``None`` (the
        default), a :class:`RegexParser` is constructed from the model's
        ``_field_patterns`` class variable.

    Returns
    -------
    ParsingResult[TModel]
        Container with ``successes`` (validated model instances) and
        ``failures`` (parser-level misses or validation errors).
    """
    output_str = _normalize_to_str(output)

    # --- resolve parser ---------------------------------------------------
    if parser is None:
        patterns = cast(dict[str, str], getattr(model, "_field_patterns", {}) or {})
        parser = RegexParser(patterns)

    # --- run parser --------------------------------------------------------
    try:
        parser_output: ParserOutput = parser.parse(output_str)
    except Exception as exc:
        result: ParsingResult[TModel] = ParsingResult()
        result.failures.append(
            ParsingFailure(
                raw_text=output_str[:500],
                attempted_patterns=[],
                exception=str(exc),
                line_number=0,
            )
        )
        return result

    # --- assemble result ---------------------------------------------------
    result = ParsingResult[TModel]()
    result.failures.extend(parser_output.failures)

    for index, record in enumerate(parser_output.records):
        try:
            instance = model(**record)
        except ValidationError as exc:
            try:
                exception_detail = exc.json()
            except Exception:
                exception_detail = str(exc)
            result.failures.append(
                ParsingFailure(
                    raw_text=str(record),
                    attempted_patterns=[],
                    exception=exception_detail,
                    line_number=index + 1,
                )
            )
            continue
        result.successes.append(instance)

    return result
