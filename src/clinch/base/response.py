# src/clinch/base/response.py
from __future__ import annotations

from typing import Any, ClassVar, Dict, Iterable, Mapping, TypeVar

from pydantic import BaseModel

from clinch.parsing import ParsingResult
from clinch.parsing.engine import parse_output as _parse_output

TResponse = TypeVar("TResponse", bound="BaseCLIResponse")


class _FieldPatternMapping:
    """Lazy, MRO-aware mapping of field name → regex pattern."""

    def __set_name__(self, owner: type[object], name: str) -> None:
        self._name = name

    def __get__(self, instance: Any, owner: type[object] | None = None) -> Mapping[str, str]:
        if owner is None:
            owner = type(instance)

        cache_name = f"__{self._name}_cache"
        cached = owner.__dict__.get(cache_name)
        if isinstance(cached, dict):
            return cached

        merged: Dict[str, str] = {}

        for base in reversed(owner.__mro__):
            extract = getattr(base, "_extract_field_patterns", None)
            if extract is None or base is object:
                continue
            try:
                patterns = extract()
            except TypeError:
                continue
            if isinstance(patterns, dict):
                merged.update(patterns)

        setattr(owner, cache_name, merged)
        return merged


class BaseCLIResponse(BaseModel):
    """Base model for all CLI response types in CLInch."""

    _field_patterns: ClassVar[Mapping[str, str]] = _FieldPatternMapping()

    def __init_subclass__(cls, **kwargs: object) -> None:  # type: ignore[override]
        super().__init_subclass__(**kwargs)

    @classmethod
    def _extract_field_patterns(cls) -> Dict[str, str]:
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
        return _parse_output(cls, output)
