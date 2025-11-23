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
    """Create a Pydantic Field with optional regex pattern metadata.

    This is a thin wrapper around :func:`pydantic.Field` that adds a
    ``pattern`` entry to the field's ``json_schema_extra`` metadata. CLInch
    uses this stored regex pattern later when parsing CLI output into
    Pydantic models.

    Args:
        default: Default value for the field. If omitted, the field is
            required, matching the behavior of :func:`pydantic.Field`.
        pattern: Optional regular expression string used to parse values
            for this field from CLI output.
        **kwargs: Additional keyword arguments forwarded directly to
            :func:`pydantic.Field` (e.g. ``description``, ``gt``, or
            an existing ``json_schema_extra`` mapping).

    Returns:
        The :class:`pydantic.fields.FieldInfo` instance created by
        :func:`pydantic.Field`.

    Example:
        >>> from pydantic import BaseModel
        >>> class Example(BaseModel):
        ...     value: str = Field(pattern=r"value: (\\w+)")
        ...
    """

    json_schema_extra = dict(kwargs.pop("json_schema_extra", {}) or {})

    if pattern is not None:
        json_schema_extra["pattern"] = pattern

    json_schema_extra_arg: Any = json_schema_extra or None

    return PydanticField(default, json_schema_extra=json_schema_extra_arg, **kwargs)
