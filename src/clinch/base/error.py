# src/clinch/base/error.py
from __future__ import annotations

from typing import Any, Self

from pydantic import create_model
from pydantic.fields import FieldInfo

from clinch.base.response import _PatternMixin
from clinch.exceptions import CLInchException
from clinch.parsing.engine import parse_output as _parse_output


class BaseCLIError(_PatternMixin, CLInchException):
    """Structured error information for failed CLI commands.

    This class is an exception type and uses Pydantic models internally
    for parsing stderr when subclasses declare pattern-based fields.
    """

    exit_code: int
    stderr: str
    stdout: str
    command: str

    def __init__(
        self,
        *,
        exit_code: int,
        stderr: str,
        stdout: str = "",
        command: str,
        **extra: Any,
    ) -> None:
        self.exit_code = exit_code
        self.stderr = stderr
        self.stdout = stdout
        self.command = command

        for name, value in extra.items():
            setattr(self, name, value)

        super().__init__(str(self))

    def __str__(self) -> str:
        stderr_preview = self.stderr
        if len(stderr_preview) > 200:
            stderr_preview = stderr_preview[:200] + "..."
        return (
            f"Command '{self.command}' failed with exit code {self.exit_code}: "
            f"{stderr_preview}"
        )

    def __init_subclass__(cls, **kwargs: object) -> None:  # type: ignore[override]
        """Populate ``_field_patterns`` for error subclasses.

        We scan for :class:`FieldInfo` descriptors on the subclass, record
        their regex patterns, and then *remove* those descriptors from the
        class so that instances do not expose the attributes unless parsing
        succeeds.  Parsed values are attached to instances by ``__init__``
        via the ``extra`` mapping.
        """
        super().__init_subclass__(**kwargs)

        merged = cls._merge_parent_patterns()
        merged.update(cls._extract_field_patterns())
        cls._field_patterns = merged

    @classmethod
    def _extract_field_patterns(cls) -> dict[str, str]:
        patterns: dict[str, str] = {}
        for name, value in list(cls.__dict__.items()):
            if not isinstance(value, FieldInfo):
                continue
            json_extra = value.json_schema_extra or {}
            pat = json_extra.get("pattern")
            if isinstance(pat, str):
                patterns[name] = pat
            # Remove the descriptor so instances only get the attribute
            # when we explicitly attach it via parsed data.
            delattr(cls, name)
        return patterns

    @classmethod
    def parse_from_stderr(
        cls,
        stderr: str,
        exit_code: int,
        command: str,
        stdout: str = "",
    ) -> Self:
        """Parse stderr into an error instance using pattern fields."""
        pattern_fields = dict(cls._field_patterns)
        pattern_data: dict[str, Any] = {}

        if pattern_fields:
            field_definitions: dict[str, tuple[type[str], Any]] = {
                name: (str, ...)
                for name in pattern_fields
            }
            PatternModel = create_model(  # noqa: N806  # type: ignore[call-arg]
                f"{cls.__name__}PatternModel",
                **field_definitions,
            )
            PatternModel._field_patterns = pattern_fields

            parse_result = _parse_output(PatternModel, stderr)
            if parse_result.successes:
                pattern_instance = parse_result.successes[0]
                pattern_data = pattern_instance.model_dump()

        data: dict[str, Any] = {
            "exit_code": exit_code,
            "stderr": stderr,
            "stdout": stdout,
            "command": command,
            **pattern_data,
        }
        return cls(**data)
