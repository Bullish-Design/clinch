# tests/test_advanced_responses.py
from __future__ import annotations

from datetime import datetime

from pydantic import computed_field, field_serializer, field_validator, model_validator

from clinch import BaseCLIResponse, Field
from clinch.parsing.engine import parse_output


class _GitBranch(BaseCLIResponse):
    name: str = Field(pattern=r"\*?\s+(\S+)")
    is_current: bool = Field(default=False, pattern=r"(\*)")

    @field_validator("is_current", mode="before")
    @classmethod
    def _coerce_is_current(cls, v: object) -> bool:
        # When the pattern matches we get the literal "*", convert that to True.
        # When it doesn't match the field is absent and the default False is used.
        if isinstance(v, str):
            return v == "*"
        return bool(v)

    @computed_field
    @property
    def short_name(self) -> str:
        return self.name.split("/")[-1]

    @computed_field
    @property
    def remote(self) -> str | None:
        parts = self.name.split("/")
        return parts[0] if len(parts) > 1 else None

    @computed_field
    @property
    def is_main_branch(self) -> bool:
        return self.short_name in {"main", "master", "develop"}


def test_computed_fields_expose_short_name_and_remote() -> None:
    _GitBranch._field_patterns = {
        "name": r"\*?\s+(\S+)",
        "is_current": r"(\*)",
    }

    output = "* main\n  origin/feature-x\n"
    result = parse_output(_GitBranch, output)

    assert result.failure_count == 0
    assert result.success_count == 2

    current, remote = result.successes

    assert current.is_current is True
    assert current.name == "main"
    assert current.short_name == "main"
    assert current.remote is None
    assert current.is_main_branch is True

    assert remote.is_current is False
    assert remote.name == "origin/feature-x"
    assert remote.short_name == "feature-x"
    assert remote.remote == "origin"
    assert remote.is_main_branch is False


class _LogEntry(BaseCLIResponse):
    timestamp: datetime = Field(pattern=r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})")
    level: str = Field(pattern=r"\s(INFO|WARN|ERROR|info|warn|error)\s")
    message: str = Field(pattern=r"-\s(.+)$")

    @field_validator("timestamp", mode="before")
    @classmethod
    def _parse_timestamp(cls, v: str) -> datetime:
        return datetime.fromisoformat(v)

    @field_validator("level", mode="after")
    @classmethod
    def _normalize_level(cls, v: str) -> str:
        return v.upper()

    @model_validator(mode="after")
    def _strip_message(self) -> _LogEntry:
        self.message = self.message.strip()
        return self


def test_type_coercion_and_model_validation_for_log_entries() -> None:
    _LogEntry._field_patterns = {
        "timestamp": r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})",
        "level": r"\s(INFO|WARN|ERROR|info|warn|error)\s",
        "message": r"-\s(.+)$",
    }

    output = (
        "2024-03-01T12:34:56 INFO - Started service\n"
        "2024-03-01T12:35:01 warn - slow request\n"
    )

    result = parse_output(_LogEntry, output)

    assert result.failure_count == 0
    assert result.success_count == 2

    first, second = result.successes

    assert isinstance(first.timestamp, datetime)
    assert first.level == "INFO"
    assert first.message == "Started service"

    assert isinstance(second.timestamp, datetime)
    assert second.level == "WARN"
    assert second.message == "slow request"


class _DockerContainer(BaseCLIResponse):
    container_id: str = Field(pattern=r"^([a-f0-9]{12})")
    status: str = Field(pattern=r"(Up|Exited)")
    # Note the "->" in the pattern – this matches "8000->8000/tcp"
    ports: str | None = Field(default=None, pattern=r"(\d+->\d+/tcp)")

    @model_validator(mode="after")
    def _normalize_and_fix_state(self) -> _DockerContainer:
        self.status = self.status.upper()
        if self.status == "EXITED":
            self.ports = None
        return self


def test_model_validator_can_fix_inconsistent_container_state() -> None:
    _DockerContainer._field_patterns = {
        "container_id": r"^([a-f0-9]{12})",
        "status": r"(Up|Exited)",
        "ports": r"(\d+->\d+/tcp)",
    }

    output = (
        "0123456789ab Up 2 minutes 0.0.0.0:8000->8000/tcp\n"
        "deadbeefdead Exited (0) 2 hours ago 0.0.0.0:5432->5432/tcp\n"
    )

    result = parse_output(_DockerContainer, output.splitlines())

    assert result.failure_count == 0
    assert result.success_count == 2

    running, exited = result.successes

    assert running.status == "UP"
    assert running.ports is not None

    assert exited.status == "EXITED"
    assert exited.ports is None


class _ProcessUsage(BaseCLIResponse):
    cpu_percent: float = Field(pattern=r"cpu=(\d+\.\d+)")
    memory_mb: int = Field(pattern=r"mem=(\d+)")

    @field_serializer("cpu_percent")
    def serialize_cpu(self, value: float) -> str:
        return f"{value:.1f}%"

    @field_serializer("memory_mb")
    def serialize_memory(self, value: int) -> str:
        if value >= 1024:
            return f"{value / 1024:.1f} GB"
        return f"{value} MB"


def test_field_serializers_control_export_format() -> None:
    _ProcessUsage._field_patterns = {
        "cpu_percent": r"cpu=(\d+\.\d+)",
        "memory_mb": r"mem=(\d+)",
    }

    output = "cpu=12.3 mem=1536"
    result = parse_output(_ProcessUsage, output)

    assert result.failure_count == 0
    assert result.success_count == 1

    usage = result.successes[0]

    # Internal types are parsed primitives
    assert isinstance(usage.cpu_percent, float)
    assert isinstance(usage.memory_mb, int)

    dumped = usage.model_dump()
    assert dumped["cpu_percent"] == "12.3%"
    assert dumped["memory_mb"] == "1.5 GB"
