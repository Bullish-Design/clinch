# src/clinch/fields.py
from __future__ import annotations

from typing import Any

from pydantic import Field as PydanticField
from pydantic_core import PydanticUndefined


def Field(  # noqa: N802
    default: Any = PydanticUndefined,
    *,
    pattern: str | None = None,
    **kwargs: Any,
) -> Any:
    """Create a Pydantic Field with optional regex pattern metadata.

    The pattern argument is stored in json_schema_extra under the
    "pattern" key so the parsing engine can discover it later.
    """
    json_schema_extra = dict(kwargs.pop("json_schema_extra", {}) or {})

    if pattern is not None:
        json_schema_extra["pattern"] = pattern

    json_schema_extra_arg: Any = json_schema_extra or None
    return PydanticField(default, json_schema_extra=json_schema_extra_arg, **kwargs)
