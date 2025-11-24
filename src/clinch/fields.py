# src/clinch/fields.py
from __future__ import annotations

from typing import Any

from pydantic import Field as PydanticField
from pydantic_core import PydanticUndefined


def Field(
    default: Any = PydanticUndefined,
    *,
    pattern: str | None = None,
    **kwargs: Any,
) -> Any:
    """Create a Pydantic Field with optional regex pattern metadata."""
    json_schema_extra = dict(kwargs.pop("json_schema_extra", {}) or {})

    if pattern is not None:
        json_schema_extra["pattern"] = pattern

    json_schema_extra_arg: Any = json_schema_extra or None
    return PydanticField(default, json_schema_extra=json_schema_extra_arg, **kwargs)
