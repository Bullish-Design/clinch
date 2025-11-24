# src/clinch/base/error.py
from __future__ import annotations

import re
from typing import Any, ClassVar, Dict, Mapping

from pydantic import Field, dataclasses

from clinch.base.response import _FieldPatternMapping
from clinch.exceptions import CLInchException


@dataclasses.dataclass(
    config={
        "arbitrary_types_allowed": True,
        "extra": "ignore",
    }
)
class BaseCLIError(CLInchException):
    """Structured error information for failed CLI commands.

    This Pydantic dataclass also behaves as an exception type. It
    captures key details about a failed command (exit code, stdout,
    stderr, and the command string) while allowing subclasses to
    declare additional pattern-based fields that are parsed from
    stderr.
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

    # Lazy mapping of field name → regex pattern, inherited and cached.
    _field_patterns: ClassVar[Mapping[str, str]] = _FieldPatternMapping()

    def __post_init__(self) -> None:
        # Initialize the underlying exception message using __str__.
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
        """Extract regex patterns from this error class's fields only.

        We support both the underlying Pydantic dataclass model fields
        and subclass attributes that are declared using ``Field``.
        """
        patterns: Dict[str, str] = {}

        # 1) Patterns from the generated Pydantic model (dataclass fields)
        model = getattr(cls, "__pydantic_model__", None)
        if model is not None:
            for name, field in model.model_fields.items():
                json_extra = field.json_schema_extra
                if not json_extra:
                    continue
                value = json_extra.get("pattern")
                if isinstance(value, str):
                    patterns[name] = value

        # 2) Patterns from subclass attributes declared directly on the class
        from pydantic.fields import FieldInfo  # local import to avoid cycle

        for name, value in cls.__dict__.items():
            if isinstance(value, FieldInfo):
                json_extra = value.json_schema_extra or {}
                pattern = json_extra.get("pattern")
                if isinstance(pattern, str):
                    patterns.setdefault(name, pattern)

        return patterns

    @classmethod
    def parse_from_stderr(
        cls,
        stderr: str,
        exit_code: int,
        command: str,
        stdout: str = "",
    ) -> "BaseCLIError":
        """Parse stderr into an error instance.

        This method scans ``stderr`` using the patterns declared on
        the subclass (if any). For each pattern-backed field, the
        first match is used to populate that field. When patterns do
        not match, a valid error instance is still returned containing
        the raw stderr and command metadata.
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
                # Only treat fields that are not part of the base dataclass
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

        # Construct the base dataclass instance first, then attach any
        # extra parsed attributes so subclasses do not need to be
        # decorated as dataclasses themselves.
        instance = cls(**base_data)
        for name, value in extra_values.items():
            setattr(instance, name, value)

        return instance
