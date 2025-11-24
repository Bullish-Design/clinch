# src/clinch/base/error.py
from __future__ import annotations

import re
from typing import Any, ClassVar, Dict, Type, TypeVar

from pydantic import Field
from pydantic.dataclasses import dataclass
from pydantic.fields import FieldInfo

from clinch.exceptions import CLInchException

TError = TypeVar("TError", bound="BaseCLIError")


class _ErrorFieldPatternsDescriptor:
    """Descriptor that lazily computes regex patterns for error subclasses."""

    _cache_attr = "__clinch_error_field_patterns__"

    def __get__(self, instance: object, owner: type["BaseCLIError"] | None) -> Dict[str, str]:
        if owner is None:
            return {}

        cached = owner.__dict__.get(self._cache_attr)
        if isinstance(cached, dict):
            return cached

        merged: Dict[str, str] = {}
        # Inherit patterns from base classes first
        for base in owner.__mro__[1:]:
            base_cached = getattr(base, self._cache_attr, None)
            if isinstance(base_cached, dict):
                merged.update(base_cached)

        # Then add patterns defined directly on this class
        merged.update(owner._extract_field_patterns())
        setattr(owner, self._cache_attr, merged)
        return merged


@dataclass
class BaseCLIError(CLInchException):
    """Base error type for CLI failures.

    This is a pydantic-powered dataclass that can be raised as an
    exception and also carries structured metadata about the failure.
    """

    exit_code: int = Field(description="The command exit code")
    stderr: str = Field(description="Standard error output")
    stdout: str = Field(default="", description="Standard output")
    command: str = Field(description="Executed command string")

    # Lazily-computed mapping: field name -> regex pattern
    _field_patterns: ClassVar[Dict[str, str]] = _ErrorFieldPatternsDescriptor()

    def __post_init__(self) -> None:
        # pydantic validation has already run at this point
        CLInchException.__init__(self, str(self))

    def __str__(self) -> str:
        stderr = self.stderr
        if len(stderr) > 200:
            stderr_preview = f"{stderr[:200]}..."
        else:
            stderr_preview = stderr
        return f"Command '{self.command}' failed with exit code {self.exit_code}: {stderr_preview}"

    @classmethod
    def _extract_field_patterns(cls) -> Dict[str, str]:
        """Extract regex patterns from pydantic dataclass field metadata and subclass Field declarations."""
        patterns: Dict[str, str] = {}

        # Patterns from pydantic dataclass fields (BaseCLIError itself)
        pyd_fields = getattr(cls, "__pydantic_fields__", {}) or {}
        for name, field_info in pyd_fields.items():
            extra = getattr(field_info, "json_schema_extra", None) or {}
            pattern = extra.get("pattern")
            if isinstance(pattern, str):
                patterns[name] = pattern

        # Patterns from FieldInfo descriptors defined directly on subclasses
        for name, value in cls.__dict__.items():
            if isinstance(value, FieldInfo):
                extra = value.json_schema_extra or {}
                pattern = extra.get("pattern")
                if isinstance(pattern, str):
                    # Do not override any base-level pattern of the same name
                    patterns.setdefault(name, pattern)

        return patterns

    @classmethod
    def parse_from_stderr(
        cls: Type[TError],
        stderr: str,
        exit_code: int,
        command: str,
        stdout: str = "",
    ) -> TError:
        """Parse stderr into a structured error instance.

        Pattern-backed fields are populated from the stderr text.
        If no patterns match, the method falls back to returning an
        instance with only the core fields set, and any matched values
        are attached as attributes afterwards.
        """
        base_kwargs: Dict[str, Any] = {
            "exit_code": exit_code,
            "stderr": stderr,
            "stdout": stdout,
            "command": command,
        }

        # Skip core fields when applying regex patterns
        patterns = {
            name: pattern
            for name, pattern in cls._field_patterns.items()
            if name not in base_kwargs
        }

        # Instantiate base error first
        error = cls(**base_kwargs)

        if not patterns:
            return error

        matched_values: Dict[str, Any] = {}
        for field_name, pattern in patterns.items():
            match = re.search(pattern, stderr)
            if not match:
                continue
            value = match.group(1) if match.groups() else match.group(0)
            matched_values[field_name] = value

        # Attach matched values as attributes (works even for subclass-only fields)
        for name, value in matched_values.items():
            setattr(error, name, value)

        return error
