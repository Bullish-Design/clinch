# Wrapper configuration and validation

`CLIWrapper` is a Pydantic `BaseModel`, which means wrapper configuration can be
validated just like any other Pydantic model. This keeps misconfigured wrappers
from failing only at runtime when a command is executed.

At minimum, every wrapper should:

* define a non-empty `command` class variable; and
* optionally override fields such as `strict_mode` and `timeout`.

For example:

```python
from clinch import CLIWrapper

class GitWrapper(CLIWrapper):
    command = "git"
    strict_mode = True
    timeout = 30
```

## Built-in validation

`CLIWrapper` already ships with some basic validation:

* `command` must be defined on the subclass, otherwise a `TypeError` is raised
  from `model_post_init`.
* `timeout` must be a positive integer and must not exceed 600 seconds. This is
  enforced with a `@field_validator("timeout")` on the base class.

These checks run when you construct a wrapper instance:

```python
git = GitWrapper()          # OK
git.timeout = 10            # OK (still validated by Pydantic on assignment)

GitWrapper(timeout=0)       # raises ValidationError (timeout must be positive)
```

## Adding wrapper-specific validation

For more complex tools you can define your own `@field_validator` or
`@model_validator` hooks on the wrapper subclass.

### Validating simple flags

```python
from pydantic import field_validator

from clinch import CLIWrapper

class ApiWrapper(CLIWrapper):
    command = "my-api"
    timeout: int = 30
    region: str = "us-east-1"

    @field_validator("region")
    @classmethod
    def validate_region(cls, value: str) -> str:
        allowed = {"us-east-1", "eu-west-1"}
        if value not in allowed:
            msg = f"unsupported region {value!r}, expected one of {sorted(allowed)}"
            raise ValueError(msg)
        return value
```

Now invalid configuration is rejected eagerly:

```python
ApiWrapper(region="unknown")   # raises ValidationError
```

### Cross-field validation

Use `@model_validator(mode="after")` when validation needs to see multiple
fields at once:

```python
from pydantic import model_validator

class GitLikeWrapper(CLIWrapper):
    command = "git"
    default_branch: str = "main"
    protected_branches: set[str] = {"main", "develop"}

    @model_validator(mode="after")
    def ensure_default_is_protected(self) -> "GitLikeWrapper":
        if self.default_branch not in self.protected_branches:
            msg = "default_branch must be included in protected_branches"
            raise ValueError(msg)
        return self
```

If you construct `GitLikeWrapper(default_branch="feature-x")` the model will
raise a `ValidationError` before any commands are executed.

## Relationship to command objects

`BaseCLICommand` is also a `BaseModel`, and you can apply the same patterns to
validate command-specific options:

```python
from clinch import BaseCLICommand, BaseCLIResponse, Field

class GitCommit(BaseCLIResponse):
    hash: str = Field(pattern=r"^([a-f0-9]{7,40})")
    message: str = Field(pattern=r"^[a-f0-9]+\s+(.+)$")

class GitLogCommand(BaseCLICommand):
    subcommand = "log"
    response_model = GitCommit

    max_count: int = 10

    @field_validator("max_count")
    @classmethod
    def validate_max_count(cls, value: int) -> int:
        if value < 1:
            raise ValueError("max_count must be positive")
        if value > 1000:
            raise ValueError("max_count must not exceed 1000")
        return value
```

See `examples/validated_wrappers.py` and `tests/test_wrapper_validation.py` for
executable examples of these patterns.
