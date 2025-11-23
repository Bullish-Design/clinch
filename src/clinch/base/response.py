# src/clinch/base/response.py
from __future__ import annotations

from typing import ClassVar, Dict, Iterable, TypeVar

from pydantic import BaseModel

from clinch.parsing import ParsingResult
from clinch.parsing.engine import parse_output as _parse_output

TResponse = TypeVar("TResponse", bound="BaseCLIResponse")


class _FieldPatternsDescriptor:
    """Descriptor that lazily computes field pattern mappings per subclass.

    This avoids relying on ``__init_subclass__`` timing, which can
    conflict with Pydantic's model construction. Instead, patterns are
    computed the first time ``_field_patterns`` is accessed on a given
    subclass and then cached on that subclass.
    """

    _cache_attr = "__clinch_field_patterns__"

    def __get__(self, instance: object, owner: type["BaseCLIResponse"] | None) -> Dict[str, str]:
        if owner is None:
            # Access via the descriptor object itself (shouldn't happen in normal use).
            return {}

        # If we've already computed patterns for this owner, return the cached value.
        cached = owner.__dict__.get(self._cache_attr)
        if isinstance(cached, dict):
            return cached

        # Merge cached patterns from base classes first.
        merged: Dict[str, str] = {}
        for base in owner.__mro__[1:]:
            base_cached = getattr(base, self._cache_attr, None)
            if isinstance(base_cached, dict):
                merged.update(base_cached)

        # Then overlay patterns defined directly on this owner.
        if hasattr(owner, "_extract_field_patterns"):
            own_patterns = owner._extract_field_patterns()
            merged.update(own_patterns)

        setattr(owner, self._cache_attr, merged)
        return merged


class BaseCLIResponse(BaseModel):
    """Base model for all CLI response types in CLInch.

    Subclasses represent structured views of CLI output. Parsing is
    performed via :meth:`parse_output`, which uses the parsing engine
    to apply regex patterns and create model instances.

    Each subclass exposes ``_field_patterns`` as a mapping of
    ``field name → regex pattern`` computed lazily from field metadata.
    """

    # Exposed as a descriptor so each subclass gets its own mapping, computed on first access.
    _field_patterns: ClassVar[Dict[str, str]] = _FieldPatternsDescriptor()

    def __init_subclass__(cls, **kwargs: object) -> None:  # type: ignore[override]
        """Ensure Pydantic's subclass initialisation still runs.

        Pattern extraction is handled lazily by the descriptor.
        """
        super().__init_subclass__(**kwargs)

    @classmethod
    def _extract_field_patterns(cls) -> Dict[str, str]:
        """Extract regex patterns from model fields.

        Looks for a ``"pattern"`` entry in ``json_schema_extra`` for each
        Pydantic field and returns a mapping of field name to pattern.
        """
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
    ) -> ParsingResult[TResponse]:
        """Parse CLI output into response instances using the engine."""
        return _parse_output(cls, output)
