# CLInch User Guide

## Install

```bash
pip install clinch
# or
uv add clinch
```

Requires Python >= 3.13. Unix-only (Linux, macOS).

## 1. Define a Response Model

A response model describes the structure of one line (or block) of CLI output. Each field has a `pattern` — a regex that extracts the value from raw text.

```python
from clinch import BaseCLIResponse, Field

class GitBranch(BaseCLIResponse):
    name: str = Field(pattern=r"\*?\s+(\S+)")
    is_current: bool = Field(default=False, pattern=r"(\*)")
```

Given the line `* main`, the engine matches `(\S+)` to extract `"main"` for `name`, and `(\*)` to extract `"*"` (truthy) for `is_current`.

### Pattern modes

```python
# Capture group — extracts group(1)
name: str = Field(pattern=r"name: (\w+)")

# Named groups — populates multiple fields from one pattern
# (put the pattern on any one of the fields it populates)
info: str = Field(pattern=r"(?P<pid>\d+)\s+(?P<name>\S+)")

# No capture group — extracts the full match (group(0))
version: str = Field(pattern=r"\d+\.\d+\.\d+")
```

### Optional fields

Fields with a default value won't cause a parse failure if the pattern doesn't match:

```python
class LogLine(BaseCLIResponse):
    timestamp: str = Field(pattern=r"^\[([^\]]+)\]")
    level: str = Field(pattern=r"\[(INFO|WARN|ERROR)\]")
    user: str | None = Field(default=None, pattern=r"user=(\w+)")  # optional
```

## 2. Define a Wrapper

A wrapper ties a CLI command to your response models and handles execution.

```python
from clinch import CLIWrapper

class GitWrapper(CLIWrapper):
    command = "git"           # required — the CLI binary name
    timeout = 30              # seconds (default: 30, max: 600)
    strict_mode = False       # raise ParsingError on any failure (default: False)

    def branches(self):
        return self._execute("branch", response_model=GitBranch)

    def log(self, n=10):
        return self._execute("log", f"--oneline", n=n, response_model=GitCommit)
```

`_execute()` takes positional args (passed as-is), keyword args (converted to `--flags`), and a `response_model`.

### Keyword argument conversion

The default `_build_args()` converts kwargs like this:

| Python | CLI |
|---|---|
| `all=True` | `--all` |
| `all=False` | *(omitted)* |
| `count=5` | `--count 5` |
| `count=None` | *(omitted)* |
| `exclude=["a", "b"]` | `--exclude a --exclude b` |
| `no_merges=True` | `--no-merges` |

Underscores become hyphens. Override `_build_args()` for different conventions.

### Preprocessing output

Override `_preprocess_output()` to clean up stdout before parsing (strip ANSI codes, remove headers, etc.):

```python
class MyWrapper(CLIWrapper):
    command = "mytool"

    def _preprocess_output(self, output: str) -> str:
        # Skip the header line
        lines = output.splitlines()
        return "\n".join(lines[1:])
```

## 3. Use the Result

`_execute()` returns a `ParsingResult[T]`:

```python
git = GitWrapper()
result = git.branches()

# Iterate over successes (ParsingResult supports iteration, len, indexing)
for branch in result:
    print(branch.name)

# Direct access
first = result[0]
count = len(result)
sliced = result[1:3]

# Check for failures
if result.has_failures:
    print(result.get_failure_summary())

# Filter and transform
current = result.filter_successes(lambda b: b.is_current)
names = result.map_successes(lambda b: b.name)  # returns ParsingResult[str]
```

## 4. Block Parsing

Some CLI tools produce multi-line records (like `git log` or `apt show`). Use `parse_blocks()` to parse these — all lines in a block are matched and merged into one model instance.

```python
class GitCommit(BaseCLIResponse):
    hash: str = Field(pattern=r"commit (\w+)")
    author: str = Field(pattern=r"Author: (.+)")
    message: str = Field(pattern=r"    (.+)")

# Blocks are separated by blank lines by default
output = """commit abc123
Author: Alice
    Fix the thing

commit def456
Author: Bob
    Add the feature"""

result = GitCommit.parse_blocks(output)
assert result[0].hash == "abc123"
assert result[1].author == "Bob"
```

You can also specify a custom delimiter:

```python
result = MyModel.parse_blocks(output, delimiter="---")
```

## 5. Error Handling

### CLI command failures

When a command exits with a non-zero status, CLInch raises a `BaseCLIError` (or your custom subclass):

```python
from clinch import BaseCLIError, Field

class GitError(BaseCLIError):
    # Optional: parse structured data from stderr
    fatal_message: str = Field(pattern=r"fatal: (.+)")

class GitWrapper(CLIWrapper):
    command = "git"
    error_model = GitError

try:
    result = git.status()
except GitError as e:
    print(e.exit_code)       # int
    print(e.stderr)          # raw stderr string
    print(e.fatal_message)   # parsed from stderr (if pattern matched)
```

### Other exceptions

```python
from clinch import CommandNotFoundError, CommandTimeoutError, ParsingError

try:
    result = wrapper.do_something()
except CommandNotFoundError:
    print("CLI tool not installed")
except CommandTimeoutError:
    print("Command took too long")
except ParsingError as e:
    # Only raised when strict_mode=True
    print(f"{len(e.failures)} lines failed to parse")
```

## 6. Async Execution

Every wrapper supports async execution via `_execute_async()`:

```python
class GitWrapper(CLIWrapper):
    command = "git"

    async def branches_async(self):
        return await self._execute_async("branch", response_model=GitBranch)

# Usage
import asyncio

async def main():
    git = GitWrapper()
    result = await git.branches_async()
    for branch in result:
        print(branch.name)

asyncio.run(main())
```

The async path uses `asyncio.create_subprocess_exec` instead of `sh`. Same interface, same error handling, same result type.

## 7. Command Objects

For reusable, validated command definitions, use `BaseCLICommand`:

```python
from clinch import BaseCLICommand

class GitLogCommand(BaseCLICommand):
    subcommand = "log"
    response_model = GitCommit

    max_count: int = 10
    oneline: bool = True

# Fields are auto-converted to CLI flags
cmd = GitLogCommand(max_count=5)
cmd.build_args()  # ["log", "--max-count", "5", "--oneline"]

# Execute via a wrapper
git = GitWrapper()
result = git.execute_command(cmd)
# or async:
result = await git.execute_command_async(cmd)
```

The same kwarg-to-flag conventions apply (None skipped, True becomes `--flag`, underscores become hyphens).

## 8. Pydantic Features

Response models are standard Pydantic models. Regex patterns get data *into* the model; Pydantic features keep it clean.

### Field validators

```python
from pydantic import field_validator

class PortInfo(BaseCLIResponse):
    port: int = Field(pattern=r":(\d+)")

    @field_validator("port")
    @classmethod
    def check_range(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError(f"Invalid port: {v}")
        return v
```

### Type coercion

```python
from datetime import datetime
from pydantic import field_validator

class LogEntry(BaseCLIResponse):
    timestamp: datetime = Field(pattern=r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})")

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_ts(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v
```

### Computed fields

```python
from pydantic import computed_field

class GitBranch(BaseCLIResponse):
    name: str = Field(pattern=r"\*?\s+(\S+)")

    @computed_field
    @property
    def short_name(self) -> str:
        return self.name.split("/")[-1]
```

### Field serializers

```python
from pydantic import field_serializer

class CpuInfo(BaseCLIResponse):
    cpu_percent: float = Field(pattern=r"(\d+\.\d+)")

    @field_serializer("cpu_percent")
    def fmt(self, v):
        return f"{v:.1f}%"

# info.model_dump() → {"cpu_percent": "42.3%"}
```

### Model validators

```python
from pydantic import model_validator

class Container(BaseCLIResponse):
    status: str = Field(pattern=r"(Up|Exited)")
    ports: str | None = Field(default=None, pattern=r"(\d+:\d+/tcp)")

    @model_validator(mode="after")
    def clean(self):
        self.status = self.status.upper()
        if self.status == "EXITED":
            self.ports = None
        return self
```

## 9. Regex Helpers

`clinch.utils.regex_helpers` provides pre-built patterns. Each has a matching form (no capture group) and a capturing form:

```python
from clinch.utils import regex_helpers

class ServerLog(BaseCLIResponse):
    timestamp: str = Field(pattern=regex_helpers.CAPTURE_ISO_DATETIME)
    ip: str = Field(pattern=regex_helpers.CAPTURE_IPV4)
    email: str = Field(pattern=regex_helpers.CAPTURE_EMAIL)
```

| Matching | Capturing | Matches |
|---|---|---|
| `ISO_DATETIME` | `CAPTURE_ISO_DATETIME` | `2024-01-15T10:30:00Z` |
| `EMAIL` | `CAPTURE_EMAIL` | `user@example.com` |
| `IPV4` | `CAPTURE_IPV4` | `192.168.1.1` |
| `IPV6` | `CAPTURE_IPV6` | `::1` |
| `URL` | `CAPTURE_URL` | `https://example.com/path` |
| `UUID` | `CAPTURE_UUID` | `550e8400-e29b-41d4-a716-446655440000` |
| `SEMVER` | `CAPTURE_SEMVER` | `1.2.3-beta+build` |
| `HEX_COLOR` | `CAPTURE_HEX_COLOR` | `#ff5733` |
| `FILE_PATH` | `CAPTURE_FILE_PATH` | `/usr/local/bin/tool` |

Use the matching form with `group(0)` extraction (no capture group in Field pattern). Use the capturing form when you want `group(1)` extraction.

## 10. Standalone Parsing

You can parse output without a wrapper — useful for testing or one-off parsing:

```python
class MyModel(BaseCLIResponse):
    name: str = Field(pattern=r"name=(\w+)")
    value: int = Field(pattern=r"value=(\d+)")

output = "name=foo value=42\nname=bar value=7"
result = MyModel.parse_output(output)

for item in result:
    print(f"{item.name}: {item.value}")
```

`parse_output()` accepts a string or any iterable of strings. Blank lines are skipped.

## 11. Wrapper Validation

Since `CLIWrapper` is a Pydantic BaseModel, you can add validators to your wrapper configuration:

```python
from pydantic import field_validator, model_validator

class ApiWrapper(CLIWrapper):
    command = "myapi"
    region: str = "us-east-1"

    @field_validator("region")
    @classmethod
    def check_region(cls, v):
        allowed = {"us-east-1", "eu-west-1"}
        if v not in allowed:
            raise ValueError(f"Unknown region: {v}")
        return v
```

Built-in validation: `command` must be defined (TypeError if missing), `timeout` must be 1-600 (ValidationError otherwise).
