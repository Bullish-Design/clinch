# src/clinch/base/error.py
from __future__ import annotations

import re
from typing import Any, ClassVar, Dict, Mapping

from pydantic import Field, dataclasses
from pydantic.fields import FieldInfo

from clinch.exceptions import CLInchException


class _FieldPatternMapping:
    """Lazy, MRO-aware mapping of field name → regex pattern for errors."""

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


@dataclasses.dataclass(
    config={
        "arbitrary_types_allowed": True,
        "extra": "ignore",
    }
)
class BaseCLIError(CLInchException):
    """Structured error information for failed CLI commands.

    This dataclass doubles as an exception type. It captures key
    pieces of information about a failed command (exit code, stdout,
    stderr, and the command string) while also allowing subclasses
    to declare additional pattern-based fields that can be parsed
    from stderr.
    """

    exit_code: int = Field(
        description="Exit code returned by the CLI command",
    )
    stderr: str = Field(
        description="Standard error output captured from the command",
    )
    stdout: str = Field(
        default="",
        description="Standard output captured from the command",
    )
    command: str = Field(
        description="The executed command string",
    )

    _field_patterns: ClassVar[Mapping[str, str]] = _FieldPatternMapping()

    def __post_init__(self) -> None:
        CLInchException.__init__(self, str(self))

    def __str__(self) -> str:
        stderr_preview = self.stderr
        if len(stderr_preview) > 200:
            stderr_preview = stderr_preview[:200] + "..."
        return (
            f"Command '{self.command}' failed with exit code {self.exit_code}: "
            f"{stderr_preview}"
        )

    @classmethod
    def _extract_field_patterns(cls) -> Dict[str, str]:
        """Extract regex patterns from both the generated model and field attributes.

        Also removes FieldInfo attributes from the class so that extra
        fields do not appear on instances unless explicitly set by
        ``parse_from_stderr``.
        """
        patterns: Dict[str, str] = {}

        # 1) From the generated Pydantic model for this dataclass.
        model = getattr(cls, "__pydantic_model__", None)
        if model is not None:
            for name, field in model.model_fields.items():
                extra = field.json_schema_extra
                if not extra:
                    continue
                value = extra.get("pattern")
                if isinstance(value, str):
                    patterns[name] = value

        # 2) From subclass attributes that are FieldInfo instances.
        to_delete: list[str] = []
        for name, value in cls.__dict__.items():
            if isinstance(value, FieldInfo):
                extra = value.json_schema_extra or {}
                pattern = extra.get("pattern")
                if isinstance(pattern, str):
                    patterns.setdefault(name, pattern)
                    to_delete.append(name)

        for name in to_delete:
            try:
                delattr(cls, name)
            except AttributeError:
                pass

        return patterns

    @classmethod
    def parse_from_stderr(
        cls,
        stderr: str,
        exit_code: int,
        command: str,
        stdout: str = "",
    ) -> "BaseCLIError":
        """Parse stderr into an error instance, populating pattern-based fields.

        If no patterns match, the returned instance still contains the
        raw stderr and command metadata.
        """
        base_data: Dict[str, Any] = {
            "exit_code": exit_code,
            "stderr": stderr,
            "stdout": stdout,
            "command": command,
        }

        extra_values: Dict[str, Any] = {}

        patterns = dict(cls._field_patterns)
        if patterns and stderr:
            for field_name, pattern in patterns.items():
                # Skip base fields to avoid overriding core metadata.
                if field_name in base_data:
                    continue
                match = re.search(pattern, stderr, re.MULTILINE)
                if not match:
                    continue
                if match.groups():
                    value: Any = match.group(1)
                else:
                    value = match.group(0)
                extra_values[field_name] = value

        instance = cls(**base_data)
        for name, value in extra_values.items():
            setattr(instance, name, value)

        return instance
