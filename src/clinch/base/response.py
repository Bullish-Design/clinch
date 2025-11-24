# src/clinch/base/response.py
from __future__ import annotations

from typing import Any, ClassVar, Dict, Iterable, TypeVar

from pydantic import BaseModel

from clinch.parsing import ParsingResult
from clinch.parsing.engine import parse_output as _parse_output

TResponse = TypeVar("TResponse", bound="BaseCLIResponse")


class BaseCLIResponse(BaseModel):
    """Base model for all CLI response types in CLInch.

    Subclasses represent structured views of CLI output. Parsing is
    performed via :meth:`parse_output`, which uses the parsing engine
    to apply regex patterns and create model instances.

    Each subclass maintains a ``_field_patterns`` mapping of field name
    → regex pattern. This mapping is populated by
    :meth:`__pydantic_init_subclass__` after Pydantic has finished
    constructing the model fields.
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
