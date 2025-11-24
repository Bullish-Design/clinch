# src/clinch/fields.py
from __future__ import annotations

from typing import Any

from pydantic import Field as _Field


def Field(
    default: Any = ...,
    *,
    pattern: str | None = None,
    json_schema_extra: dict[str, Any] | None = None,
    **kwargs: Any,
) -> Any:
    """Wrapper around :func:`pydantic.Field` that stores a regex pattern.

    The pattern is stored in ``json_schema_extra['pattern']`` so that
    response and error models can discover it for parsing.
    """
    extra: dict[str, Any] = dict(json_schema_extra or {})
    if pattern is not None:
        extra["pattern"] = pattern

    if extra:
        kwargs["json_schema_extra"] = extra

    return _Field(default, **kwargs)
