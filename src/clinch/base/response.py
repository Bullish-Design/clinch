# src/clinch/base/response.py
from __future__ import annotations

from typing import Any, ClassVar, Dict, Iterable, TypeVar

from pydantic import BaseModel

from clinch.parsing import ParsingResult
from clinch.parsing.engine import parse_output as _parse_output

TResponse = TypeVar("TResponse", bound="BaseCLIResponse")


class BaseCLIResponse(BaseModel):
    """Base model for all CLI response types in CLInch.

    Subclasses map raw CLI output into validated Pydantic models. Fields typically
    declare regex extraction patterns using :func:`clinch.Field`, and parsing is
    performed via :meth:`parse_output`, which delegates to the parsing engine.

    Response models support the full range of Pydantic features, including
    computed fields, validators, type coercion, and custom serializers. These
    features run *after* regex extraction, so you can treat parsed values like
    normal Pydantic models.

    Computed fields
    ----------------
    Derived values can be added with :func:`pydantic.computed_field` and are
    included in normal ``model_dump`` calls::

        from pydantic import computed_field
        from clinch import BaseCLIResponse, Field

        class GitBranch(BaseCLIResponse):
            name: str = Field(pattern=r"\*?\s+(\S+)")

            @computed_field
            @property
            def short_name(self) -> str:
                return self.name.split("/")[-1]

    Model validators
    ----------------
    Use :func:`pydantic.model_validator` for cross-field validation or
    normalization after parsing::

        from pydantic import model_validator

        class ProcessInfo(BaseCLIResponse):
            status: str = Field(pattern=r"(\w+)")

            @model_validator(mode="after")
            def normalize_status(self) -> "ProcessInfo":
                self.status = self.status.upper()
                return self

    Type coercion
    -------------
    Use :func:`pydantic.field_validator` with ``mode="before"`` to coerce raw
    string values into richer types (for example datetimes or enums)::

        from datetime import datetime
        from pydantic import field_validator

        class LogEntry(BaseCLIResponse):
            timestamp: datetime = Field(pattern=r"(\d{4}-\d{2}-\d{2})")

            @field_validator("timestamp", mode="before")
            @classmethod
            def parse_timestamp(cls, value: str | datetime) -> datetime:
                if isinstance(value, str):
                    return datetime.fromisoformat(value)
                return value

    Field serializers
    ------------------
    Use :func:`pydantic.field_serializer` to control how values are exported,
    without changing the internal representation::

        from pydantic import field_serializer

        class ProcessUsage(BaseCLIResponse):
            cpu_percent: float = Field(pattern=r"(\d+\.\d+)")

            @field_serializer("cpu_percent")
            def format_cpu(self, value: float) -> str:
                return f"{value:.1f}%"

    In general, treat CLI response models like any other Pydantic model: regex
    patterns get the data *into* the model, and Pydantic features keep that data
    clean, well-typed, and convenient to work with.
    """

    _field_patterns: ClassVar[Dict[str, str]] = {}

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:  # type: ignore[override]
        """Populate ``_field_patterns`` when a subclass is defined.

        We rely on Pydantic's ``__pydantic_init_subclass__`` hook so that
        ``model_fields`` is fully initialized before we attempt to extract
        regex patterns from ``json_schema_extra``.
        """
        super().__pydantic_init_subclass__(**kwargs)

        merged: Dict[str, str] = {}
        for base in cls.__mro__[1:]:
            patterns = getattr(base, "_field_patterns", None)
            if isinstance(patterns, dict):
                merged.update(patterns)

        merged.update(cls._extract_field_patterns())
        cls._field_patterns = merged

    @classmethod
    def _extract_field_patterns(cls) -> Dict[str, str]:
        """Return a mapping of field name → regex pattern for this model.","""
        patterns: Dict[str, str] = {}
        for name, field in cls.model_fields.items():
            json_extra = field.json_schema_extra
            if not json_extra:
                continue
            value = json_extra.get("pattern")
            if isinstance(value, str):
                patterns[name] = value
        return patterns

    @classmethod
    def parse_output(
        cls: type[TResponse],
        output: str | Iterable[str],
    ) -> ParsingResult[TResponse]:  # type: ignore[type-var]
        """Parse CLI output into response instances using the engine."""
        return _parse_output(cls, output)
