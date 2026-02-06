# CLInch

**Pydantic-based library for wrapping CLI tools with type-safe Python interfaces.**

CLInch turns raw CLI output into validated Pydantic models. Define regex patterns on your fields, point at a command, and get typed Python objects back — with partial failure tracking, async support, and structured error handling.

## Install

```bash
pip install clinch
# or
uv add clinch
```

Requires Python >= 3.13, Pydantic >= 2.10, sh >= 2.0. Unix-only (Linux, macOS).

## Quick Example

```python
from clinch import CLIWrapper, BaseCLIResponse, Field

class DiskUsage(BaseCLIResponse):
    filesystem: str = Field(pattern=r"^(\S+)")
    use_percent: str = Field(pattern=r"(\d+%)")
    mount: str = Field(pattern=r"(\S+)$")

class DfWrapper(CLIWrapper):
    command = "df"

    def usage(self):
        return self._execute("-h", response_model=DiskUsage)

df = DfWrapper()
result = df.usage()

for disk in result.successes:
    print(f"{disk.filesystem} mounted at {disk.mount}: {disk.use_percent} used")

if result.has_failures:
    print(f"{result.failure_count} lines could not be parsed")
```

## How It Works

1. **Define a response model** — a `BaseCLIResponse` subclass where each field has a `pattern` for regex extraction.
2. **Define a wrapper** — a `CLIWrapper` subclass that sets `command` and exposes methods calling `_execute()`.
3. **Call it** — CLInch runs the command via `sh`, splits stdout into lines, matches each line against your patterns, and returns a `ParsingResult` containing typed `successes` and detailed `failures`.

Patterns support three extraction modes:
- **Capture group**: `r"name: (\w+)"` — extracts `group(1)`
- **Named groups**: `r"(?P<pid>\d+)\s+(?P<name>\S+)"` — populates multiple fields from one pattern
- **Full match**: `r"\d+"` (no groups) — extracts `group(0)`

## Documentation

- **[USER_GUIDE.md](USER_GUIDE.md)** — Quick-start guide with practical examples covering response models, wrappers, block parsing, error handling, async, validators, and regex helpers.
- **[DEV_GUIDE.md](DEV_GUIDE.md)** — Architecture overview, codebase map, design patterns, and testing guide for contributors and maintainers.

## API at a Glance

| Export | Purpose |
|---|---|
| `BaseCLIResponse` | Base model for CLI output — define fields with `Field(pattern=...)` |
| `CLIWrapper` | Base class for CLI tool wrappers — set `command`, call `_execute()` |
| `BaseCLICommand` | Reusable command objects with auto-generated CLI args |
| `BaseCLIError` | Structured exception with `exit_code`, `stderr`, optional pattern parsing |
| `ParsingResult[T]` | Container: `successes: list[T]`, `failures: list[ParsingFailure]` |
| `ParsingFailure` | Details on a failed parse: `raw_text`, `line_number`, `attempted_patterns` |
| `Field` | Pydantic Field wrapper that stores a `pattern` in metadata |
| `regex_helpers` | Pre-built patterns: `ISO_DATETIME`, `EMAIL`, `IPV4`, `URL`, `UUID`, etc. |
| `ParsingError` | Raised in strict mode when any line fails to parse |
| `CommandNotFoundError` | Raised when the CLI command is not in PATH |
| `CommandTimeoutError` | Raised when execution exceeds the timeout |

## License

MIT — see [LICENSE](LICENSE).
