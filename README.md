# README.md

# CLInch

**Type-safe Python wrappers for CLI tools**

CLInch is a Pydantic-based library for wrapping Unix CLI tools with typed Python interfaces. Define your CLI output structure with Pydantic models and regex patterns—CLInch handles execution, parsing, and error handling.

[![PyPI version](https://badge.fury.io/py/clinch.svg)](https://badge.fury.io/py/clinch)
[![Python versions](https://img.shields.io/pypi/pyversions/clinch.svg)](https://pypi.org/project/clinch/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Quick Start

```python
from clinch import CLIWrapper, BaseCLIResponse, Field

class GitBranch(BaseCLIResponse):
    name: str = Field(pattern=r'\*?\s+(\S+)')
    is_current: bool = Field(default=False, pattern=r'(\*)')

class GitWrapper(CLIWrapper):
    command = "git"
    
    def branches(self):
        return self._execute("branch", response_model=GitBranch)

# Use it
git = GitWrapper()
result = git.branches()

for branch in result.successes:
    marker = '→' if branch.is_current else ' '
    print(f"{marker} {branch.name}")
```

## Installation

```bash
# Using uv (recommended)
uv add clinch

# Using pip
pip install clinch
```

## Why CLInch?

**Before CLInch:**
```python
import subprocess

result = subprocess.run(["git", "branch"], capture_output=True, text=True)
branches = []
for line in result.stdout.splitlines():
    if line.strip():
        is_current = line.startswith('*')
        name = line.strip().lstrip('* ')
        branches.append({'name': name, 'is_current': is_current})
```

**With CLInch:**
```python
class GitBranch(BaseCLIResponse):
    name: str = Field(pattern=r'\*?\s+(\S+)')
    is_current: bool = Field(default=False, pattern=r'(\*)')

result = git.branches()  # Fully typed, validated Python objects
```

## Core Features

- **Type-Safe**: Full mypy/pyright support with Pydantic validation
- **Declarative**: Define output structure with regex patterns in Field metadata
- **Partial Failures**: Track successful parses separately from failures
- **Error Handling**: Parse CLI errors into typed exceptions
- **Flexible**: Override argument building, parsing, error handling
- **Zero Modifications**: Works with any existing CLI tool

## Key Concepts

### Response Models

Define CLI output structure using Pydantic models with regex patterns:

```python
from clinch import BaseCLIResponse, Field
from clinch.utils import regex_helpers

class ServerLog(BaseCLIResponse):
    timestamp: str = Field(pattern=regex_helpers.ISO_DATETIME)
    level: str = Field(pattern=r'\[(INFO|WARN|ERROR)\]')
    message: str = Field(pattern=r'\]\s+(.+)$')
```

### CLI Wrappers

Inherit from `CLIWrapper` to create tool-specific interfaces:

```python
from clinch import CLIWrapper

class DockerWrapper(CLIWrapper):
    command = "docker"
    timeout = 30  # Optional timeout in seconds
    
    def ps(self, all_containers=False):
        return self._execute(
            "ps",
            all=all_containers,
            response_model=ContainerInfo
        )
```

### Partial Failure Tracking

CLInch separates successful parses from failures:

```python
result = wrapper.parse_logs()

# Access successful parses
for log in result.successes:
    process_log(log)

# Inspect failures
if result.has_failures:
    print(f"Failed to parse {result.failure_count} lines")
    for failure in result.failures:
        print(f"Line {failure.line_number}: {failure.raw_text}")
```

## Usage Examples

### Simple Wrapper

```python
from clinch import CLIWrapper, BaseCLIResponse, Field

class EchoResponse(BaseCLIResponse):
    text: str = Field(pattern=r'(.+)')

class EchoWrapper(CLIWrapper):
    command = "echo"
    
    def say(self, message: str):
        return self._execute(message, response_model=EchoResponse)

echo = EchoWrapper()
result = echo.say("hello world")
print(result.successes[0].text)  # "hello world"
```

### Multiple Line Parsing

```python
from clinch import BaseCLIResponse, Field

class ProcessInfo(BaseCLIResponse):
    pid: int = Field(pattern=r'^\s*(\d+)')
    cpu: float = Field(pattern=r'(\d+\.\d+)%')
    command: str = Field(pattern=r'\s+(\S+)$')

class PsWrapper(CLIWrapper):
    command = "ps"
    
    def processes(self):
        return self._execute("aux", response_model=ProcessInfo)

ps = PsWrapper()
result = ps.processes()

# All successfully parsed processes
for proc in result.successes:
    print(f"PID {proc.pid}: {proc.command} ({proc.cpu}% CPU)")
```

### Custom Argument Building

```python
class CustomWrapper(CLIWrapper):
    command = "mytool"
    
    def _build_args(self, **kwargs):
        # Custom flag formatting
        return [f"--{k}={v}" for k, v in kwargs.items()]
    
    def fetch(self, limit=10):
        # Becomes: mytool fetch --limit=10
        return self._execute("fetch", limit=limit, response_model=MyResponse)
```

### Error Handling

```python
from clinch import BaseCLIError, Field

class GitError(BaseCLIError):
    error_code: str = Field(pattern=r'fatal: (.+)')

class GitWrapper(CLIWrapper):
    command = "git"
    error_model = GitError  # Use custom error parser
    
    def status(self):
        try:
            return self._execute("status", response_model=StatusResponse)
        except GitError as e:
            print(f"Git error: {e.error_code}")
            print(f"Exit code: {e.exit_code}")
```

### Strict Mode

```python
class StrictWrapper(CLIWrapper):
    command = "tool"
    strict_mode = True  # Raises ParsingError on any parse failure
    
    def get_data(self):
        # Will raise ParsingError if any output line fails to parse
        return self._execute("data", response_model=DataModel)
```

### Using Regex Helpers

```python
from clinch.utils import regex_helpers

class LogEntry(BaseCLIResponse):
    timestamp: str = Field(pattern=regex_helpers.ISO_DATETIME)
    email: str = Field(pattern=regex_helpers.EMAIL)
    ip: str = Field(pattern=regex_helpers.IPV4)
    message: str = Field(pattern=r'- (.+)$')
```

Available patterns:
- `ISO_DATETIME` - ISO 8601 timestamps
- `EMAIL` - Email addresses
- `IPV4`, `IPV6` - IP addresses
- `URL` - HTTP/HTTPS URLs
- `UUID` - UUIDs
- `SEMVER` - Semantic versions (e.g., "1.2.3")
- `HEX_COLOR` - Hex color codes
- `FILE_PATH` - Unix file paths

## Configuration Options

### Wrapper Configuration

```python
class ConfiguredWrapper(CLIWrapper):
    command = "mytool"
    
    # Configuration attributes
    strict_mode = False        # Raise on parsing failures
    timeout = 30               # Command timeout in seconds
    error_model = CustomError  # Custom error parsing class
```

### Response Model Validation

Add Pydantic validators for post-parsing validation:

```python
from pydantic import field_validator

class ValidatedResponse(BaseCLIResponse):
    port: int = Field(pattern=r':(\d+)')
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError(f"Port {v} out of valid range")
        return v
```

## API Reference

### Classes

#### `BaseCLIResponse`
Base Pydantic model for CLI output parsing.

```python
class MyResponse(BaseCLIResponse):
    field: str = Field(pattern=r'pattern: (.+)')
```

**Methods:**
- `parse_output(stdout: str) -> ParsingResult[Self]` - Parse CLI output

#### `CLIWrapper`
Base class for CLI tool wrappers.

**Attributes:**
- `command: str` - **Required.** CLI command name
- `strict_mode: bool = False` - Raise on parsing failures
- `timeout: int | None = None` - Command timeout
- `error_model: Type[BaseCLIError] = BaseCLIError` - Error model class

**Methods:**
- `_execute(subcommand, *args, response_model, **kwargs)` - Execute CLI command
- `_build_args(**kwargs) -> list[str]` - Override to customize arguments
- `_preprocess_output(stdout) -> str` - Override to preprocess output

#### `ParsingResult[T]`
Container for parsing results.

**Fields:**
- `successes: list[T]` - Successfully parsed instances
- `failures: list[ParsingFailure]` - Failed parses

**Properties:**
- `has_failures: bool` - True if any failures
- `success_count: int` - Number of successes
- `failure_count: int` - Number of failures

#### `ParsingFailure`
Details about a parsing failure.

**Fields:**
- `raw_text: str` - Original line that failed
- `attempted_patterns: list[str]` - Patterns tried
- `exception: str | None` - Exception message
- `line_number: int` - Line number (1-indexed)

#### `BaseCLIError`
Base exception for CLI errors.

**Fields:**
- `exit_code: int` - Command exit code
- `stderr: str` - Standard error output
- `stdout: str` - Standard output
- `command: str` - Executed command

### Field Function

```python
Field(default=..., *, pattern: str | None = None, **kwargs)
```

Custom Field wrapper that stores regex pattern in metadata.

**Parameters:**
- `default` - Default value
- `pattern` - Regex pattern for extraction
- `**kwargs` - Other Pydantic Field arguments

## Testing Your Wrappers

```python
import pytest
from my_wrappers import GitWrapper

def test_git_branches():
    git = GitWrapper()
    result = git.branches()
    
    assert result.success_count > 0
    assert result.failure_count == 0
    
    # Check for current branch
    current = [b for b in result.successes if b.is_current]
    assert len(current) == 1
```

## Common Patterns

### Handling Optional Fields

```python
class LogEntry(BaseCLIResponse):
    timestamp: str = Field(pattern=r'^\[([^\]]+)\]')
    level: str = Field(pattern=r'\[([A-Z]+)\]')
    # Optional field - won't cause parse failure if missing
    user: str | None = Field(default=None, pattern=r'user=(\w+)')
```

### Parsing Multiple Output Formats

```python
class FlexibleParser(CLIWrapper):
    command = "tool"
    
    def get_data(self):
        result = self._execute("data", response_model=DataModel)
        
        # Retry failures with alternative pattern
        for failure in result.failures:
            recovered = failure.retry_with_pattern(r'alt: (\w+)')
            if recovered:
                result.successes.append(recovered)
        
        return result
```

### Complex Models with Nested Data

```python
class ServerInfo(BaseCLIResponse):
    hostname: str = Field(pattern=r'Host: (\S+)')
    ip: str = Field(pattern=regex_helpers.IPV4)
    port: int = Field(pattern=r':(\d+)')
    
    @property
    def connection_string(self):
        return f"{self.hostname}:{self.port}"
```

## Requirements

- Python ≥3.13
- pydantic ≥2.10
- sh ≥2.0

## Limitations

- Unix-like systems only (Linux, macOS)
- No interactive CLI tools (stdin interaction)
- No binary output parsing
- Synchronous execution only (no async)

## FAQ

**Q: How is CLInch different from subprocess?**

CLInch adds type safety, declarative parsing, and partial failure tracking on top of CLI execution. Instead of manual string parsing, you define output structure once and get validated Python objects.

**Q: Do I need to know regex?**

Basic patterns like `r'name: (\w+)'` are straightforward. The `regex_helpers` module provides common patterns. Complex tools may require more sophisticated patterns.

**Q: What if CLI output changes?**

Update your response model's Field patterns. If you have tests, they'll catch breaking changes. Partial failure tracking helps identify which patterns need adjustment.

**Q: Can I use this on Windows?**

The `sh` library is Unix-focused. For Windows, consider using `subprocess` directly or contributing Windows support.

**Q: How do I handle commands with many subcommands?**

Pass subcommands as arguments:
```python
def pr_list(self):
    return self._execute("pr", "list", response_model=PR)
```

## Development

```bash
# Clone repository
git clone https://github.com/user/clinch.git
cd clinch

# Install dependencies
uv sync

# Run tests
uv run pytest

# Type checking
uv run mypy src/

# Linting
uv run ruff check src/
uv run ruff format src/
```

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all quality checks pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
