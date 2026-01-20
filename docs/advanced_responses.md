# Advanced Response Models

This guide shows how to take full advantage of Pydantic when defining
`BaseCLIResponse` subclasses. All of the features below run *after* CLInch has
used regex patterns to populate your model fields.

The examples assume:

```python
from datetime import datetime

from pydantic import computed_field, field_serializer, field_validator, model_validator

from clinch import BaseCLIResponse, Field
```

## Computed fields

Use `@computed_field` to add derived values that are included in
`model_dump()` and friends:

```python
from pydantic import computed_field

class GitBranch(BaseCLIResponse):
    name: str = Field(pattern=r"\*?\s+(\S+)")

    @computed_field
    @property
    def short_name(self) -> str:
        return self.name.split("/")[-1]

    @computed_field
    @property
    def remote(self) -> str | None:
        parts = self.name.split("/")
        return parts[0] if len(parts) > 1 else None
```

## Model validators

Use `@model_validator` for cross-field validation and normalization that should
run after parsing:

```python
from pydantic import model_validator

class DockerContainer(BaseCLIResponse):
    container_id: str = Field(pattern=r"^([a-f0-9]{12})")
    status: str = Field(pattern=r"(Up|Exited)")
    ports: str | None = Field(pattern=r"(\d+:\d+/tcp)", default=None)

    @model_validator(mode="after")
    def normalize(self) -> "DockerContainer":
        # Normalize case
        self.status = self.status.upper()

        # Avoid lying about ports on stopped containers
        if self.status == "EXITED":
            self.ports = None

        return self
```

## Type coercion

Use `@field_validator(..., mode="before")` to convert raw strings into richer
types such as `datetime` or enums:

```python
from datetime import datetime
from pydantic import field_validator

class LogEntry(BaseCLIResponse):
    timestamp: datetime = Field(pattern=r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})")
    message: str = Field(pattern=r"- (.+)$")

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, value: str | datetime) -> datetime:
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value
```

## Field serializers

Use `@field_serializer` to control how values are exported without changing the
internal representation:

```python
from pydantic import field_serializer

class ProcessUsage(BaseCLIResponse):
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
```

## Putting it together

A single model can combine all of these techniques:

```python
class GitBranchInfo(BaseCLIResponse):
    name: str = Field(pattern=r"\*?\s+(\S+)")
    last_updated: datetime = Field(pattern=r"(\d{4}-\d{2}-\d{2})")
    ahead_by: int = Field(pattern=r"ahead (\d+)", default=0)
    behind_by: int = Field(pattern=r"behind (\d+)", default=0)

    @field_validator("last_updated", mode="before")
    @classmethod
    def parse_date(cls, value: str | datetime) -> datetime:
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value

    @computed_field
    @property
    def short_name(self) -> str:
        return self.name.split("/")[-1]

    @computed_field
    @property
    def is_main_branch(self) -> bool:
        return self.short_name in {"main", "master", "develop", "trunk"}

    @computed_field
    @property
    def divergence(self) -> int:
        return self.ahead_by + self.behind_by

    @field_serializer("last_updated")
    def serialize_date(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%d")
```

See `examples/advanced_responses.py` and `tests/test_advanced_responses.py` for
executable versions of these patterns.
