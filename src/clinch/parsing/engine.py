"""Parsing engine — orchestrates parser → Pydantic model construction.

This module is the bridge between raw parser output and validated
Pydantic model instances.  It accepts an optional :class:`Parser`
implementation (defaulting to :class:`RegexParser` with the model's
``_field_patterns``) and handles model construction, validation-error
tracking, and :class:`ParsingResult` assembly.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, cast, get_args

from pydantic import BaseModel, TypeAdapter, ValidationError

from clinch.parsing.protocol import Parser, ParserOutput
from clinch.parsing.regex_parser import RegexParser, _compile
from clinch.parsing.result import ParsingFailure, ParsingResult

_BOOL_ADAPTER = TypeAdapter(bool)


def _is_bool_annotation(annotation: Any) -> bool:
    """Whether the annotation is ``bool`` or ``bool | None``."""
    if annotation is bool:
        return True
    args = get_args(annotation)
    return len(args) == 2 and bool in args and type(None) in args


def _coerce_bool_fields(model: type[BaseModel], record: dict[str, Any]) -> dict[str, Any]:
    """Apply pattern-presence semantics to bool-typed fields.

    Parsers return raw text.  For a bool-typed field, captured text that
    Pydantic can coerce (``yes``/``no``/``1``/``0``/``true``/``false``/...)
    is passed through unchanged; any other captured marker (e.g. ``*`` for
    ``git branch``) means the pattern matched, i.e. ``True``.  Fields the
    pattern did not match are absent from the record and keep their default.
    """
    coerced = record
    for name, value in record.items():
        if isinstance(value, bool):
            continue
        field = model.model_fields.get(name)
        if field is None or not _is_bool_annotation(field.annotation):
            continue
        try:
            coerced_value: Any = _BOOL_ADAPTER.validate_python(value)
        except ValidationError:
            coerced_value = True
        if coerced is record:
            coerced = dict(record)
        coerced[name] = coerced_value
    return coerced


def clear_pattern_cache() -> None:
    """Clear the compiled regex pattern cache."""
    _compile.cache_clear()


def get_cache_info() -> dict[str, int]:
    """Return basic statistics about the compiled pattern cache."""
    info = _compile.cache_info()
    maxsize = info.maxsize if info.maxsize is not None else 0
    return {
        "hits": info.hits,
        "misses": info.misses,
        "size": info.currsize,
        "maxsize": maxsize,
    }


def _normalize_to_str(output: str | Iterable[str]) -> str:
    """Normalize CLI output into a single string."""
    if isinstance(output, str):
        return output
    return "\n".join(output)


def parse_output[TModel: BaseModel](
    model: type[TModel],
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
            instance = model(**_coerce_bool_fields(model, record))
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
