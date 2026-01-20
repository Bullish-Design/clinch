# examples/advanced_responses.py
from __future__ import annotations

from datetime import datetime

from pydantic import computed_field, field_serializer, field_validator, model_validator

from clinch import BaseCLIResponse, Field
from clinch.parsing.engine import parse_output


class GitBranch(BaseCLIResponse):
    """Example showing computed fields on a branch model."""

    name: str = Field(pattern=r"\*?\s+(\S+)")
    is_current: bool = Field(default=False, pattern=r"(\*)")

    @computed_field
    @property
    def short_name(self) -> str:
        """Branch name without any remote prefix."""
        return self.name.split("/")[-1]

    @computed_field
    @property
    def remote(self) -> str | None:
        """Remote name if this is a remote branch, otherwise None."""
        parts = self.name.split("/")
        return parts[0] if len(parts) > 1 else None

    @computed_field
    @property
    def is_main_branch(self) -> bool:
        """Whether this branch is one of the common primary branches."""
        return self.short_name in {"main", "master", "develop", "trunk"}


class LogEntry(BaseCLIResponse):
    """Example showing type coercion and model-level validation."""

    timestamp: datetime = Field(pattern=r"(\d{4}-\d{2}-\d{2})")
    level: str = Field(pattern=r"(INFO|WARN|ERROR)")
    message: str = Field(pattern=r"- (.+)$")

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, value: str | datetime) -> datetime:
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value

    @model_validator(mode="after")
    def normalize_level(self) -> "LogEntry":
        self.level = self.level.upper()
        return self


class ProcessUsage(BaseCLIResponse):
    """Example showing serializers for nicer exports."""

    cpu_percent: float = Field(pattern=r"(\d+\.\d+)")
    memory_mb: int = Field(pattern=r"(\d+)")

    @field_serializer("cpu_percent")
    def format_cpu(self, value: float) -> str:
        return f"{value:.1f}%"

    @field_serializer("memory_mb")
    def format_memory(self, value: int) -> str:
        if value >= 1024:
            return f"{value / 1024:.1f} GB"
        return f"{value} MB"


def demo_git_branch(output: str) -> list[GitBranch]:
    """Parse a git-branch-like output string into GitBranch models."""
    # For library users the usual pattern is: GitBranch.parse_output(output)
    # This helper uses the engine directly to keep the example explicit.
    GitBranch._field_patterns = {
        "name": r"\*?\s+(\S+)",
        "is_current": r"(\*)",
    }
    result = parse_output(GitBranch, output)
    return result.successes


def demo_log_entries(output: str) -> list[LogEntry]:
    """Parse log lines into LogEntry instances."""
    LogEntry._field_patterns = {
        "timestamp": r"(\d{4}-\d{2}-\d{2})",
        "level": r"(INFO|WARN|ERROR)",
        "message": r"- (.+)$",
    }
    result = parse_output(LogEntry, output)
    return result.successes


def demo_process_usage(output: str) -> list[ProcessUsage]:
    """Parse process usage lines into ProcessUsage instances."""
    ProcessUsage._field_patterns = {
        "cpu_percent": r"(\d+\.\d+)",
        "memory_mb": r"(\d+)",
    }
    result = parse_output(ProcessUsage, output)
    return result.successes
