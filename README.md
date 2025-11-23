# README.md

# CLInch

[![PyPI version](https://badge.fury.io/py/clinch.svg)](https://badge.fury.io/py/clinch)
[![Python versions](https://img.shields.io/pypi/pyversions/clinch.svg)](https://pypi.org/project/clinch/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Secure your CLI tools with type safety.**

CLInch is a Pydantic-based library for wrapping Unix CLI tools with typed Python interfaces. It eliminates boilerplate when creating Python wrappers by providing declarative, type-safe output parsing using regex patterns and Pydantic models.

## Installation

### Using UV (Recommended)
```bash
uv add clinch
```

### Using pip
```bash
pip install clinch
```

### Development Installation
```bash
git clone https://github.com/user/clinch.git
cd clinch
uv sync
```

## Quick Start

```python
from clinch import CLIWrapper, BaseCLIListResponse
from pydantic import Field

class GitBranch(BaseCLIListResponse):
    """Parsed git branch entry"""
    name: str = Field(pattern=r'\*?\s+(\S+)')
    is_current: bool = Field(default=False, pattern=r'(\*)')

class GitWrapper(CLIWrapper):
    command = "git"
    
    def branch(self) -> list[GitBranch]:
        return self._execute("branch", response_model=GitBranch)

# Use it
git = GitWrapper()
result = git.branch()

for branch in result.successes:
    marker = '→' if branch.is_current else ' '
    print(f"{marker} {branch.name}")

# Handle any parsing failures
if result.has_failures:
    print(f"\nWarning: {result.failure_count} branches failed to parse")
```

## Features

- **Type-Safe CLI Wrapping**: Define CLI output structure with Pydantic models
- **Declarative Parsing**: Use regex patterns in Field metadata for automatic parsing
- **Partial Failure Handling**: Track which outputs parsed successfully vs. failed
- **Structured Errors**: Parse CLI errors into typed exception objects
- **Flexible Configuration**: Override argument building, parsing, and error handling
- **Common Pattern Library**: Built-in regex helpers for dates, emails, IPs, URLs
- **Zero Modifications**: Works with any existing CLI tool
- **Full Type Support**: Complete mypy and pyright compatibility

## Core Concepts

### Key Abstractions
- **BaseCLIResponse**: Pydantic model for single parsed CLI outputs
- **BaseCLIListResponse**: Pydantic model for parsing multiple results from CLI output
- **BaseCLIError**: Structured error information from failed CLI commands
- **CLIWrapper**: Base class for creating tool-specific wrappers
- **ParsingResult**: Container holding successfully parsed results and any failures

### Design Philosophy

CLInch follows a "Pydantic-first" approach where CLI output parsing is declarative:
- Define output structure using Pydantic models
- Specify regex patterns in Field metadata
- Let CLInch handle execution, parsing, and validation
- Get type-safe Python objects with full IDE support

The library is **explicit over implicit**: regex patterns must be declared, non-zero exit codes raise exceptions by default, and all matches are extracted (not just the first).

## Usage

### Basic Operations

#### Creating a Simple Wrapper

```python
from clinch import CLIWrapper, BaseCLIResponse
from pydantic import Field

class DockerVersion(BaseCLIResponse):
    """Parse 'docker --version' output"""
    version: str = Field(pattern=r'Docker version (\S+)')
    
class DockerWrapper(CLIWrapper):
    command = "docker"
    
    def version(self) -> DockerVersion:
        return self._execute("--version", response_model=DockerVersion)

docker = DockerWrapper()
info = docker.version()
print(f"Docker version: {info.version}")
```

#### Parsing List Outputs

```python
class ProcessInfo(BaseCLIListResponse):
    """Parse ps output"""
    pid: int = Field(pattern=r'^\s*(\d+)')
    command: str = Field(pattern=r'\s+(\S+)$')

class PsWrapper(CLIWrapper):
    command = "ps"
    
    def list_processes(self) -> list[ProcessInfo]:
        return self._execute("aux", response_model=ProcessInfo)

ps = PsWrapper()
result = ps.list_processes()

# Access successful parses
for proc in result.successes:
    print(f"PID {proc.pid}: {proc.command}")

# Inspect failures
if result.failures:
    print(f"Failed to parse {len(result.failures)} lines")
```

### Advanced Features

#### Custom Argument Formatting

Override `_build_args()` to customize how Python parameters become CLI arguments:

```python
class CustomWrapper(CLIWrapper):
    command = "mytool"
    
    def _build_args(self, **kwargs) -> list[str]:
        """Custom argument builder"""
        args = []
        for key, value in kwargs.items():
            if isinstance(value, bool):
                if value:
                    args.append(f"--{key.replace('_', '-')}")
            else:
                args.extend([f"--{key.replace('_', '-')}", str(value)])
        return args
    
    def fetch(self, max_count: int = 10, verbose: bool = False):
        # Becomes: mytool fetch --max-count 10 --verbose
        return self._execute("fetch", max_count=max_count, verbose=verbose, 
                           response_model=MyResponse)
```

#### Strict Parsing Mode

Enable strict mode to raise exceptions on any parsing failures:

```python
class StrictWrapper(CLIWrapper):
    command = "tool"
    strict_mode = True  # Raises exception if any line fails to parse
    
    def get_data(self):
        # Will raise ParsingError if any output line doesn't match patterns
        return self._execute("data", response_model=MyModel)
```

#### Using Regex Helpers

```python
from clinch.utils import regex_helpers

class LogEntry(BaseCLIListResponse):
    """Parse log files with common patterns"""
    timestamp: str = Field(pattern=regex_helpers.ISO_DATETIME)
    email: str = Field(pattern=regex_helpers.EMAIL)
    ipv4: str = Field(pattern=regex_helpers.IPV4)
    message: str = Field(pattern=r'- (.+)$')
```

### Configuration

#### Wrapper Configuration

```python
class ConfiguredWrapper(CLIWrapper):
    command = "mytool"
    
    # Configuration options
    strict_mode = False          # Don't raise on parsing failures
    timeout = 30                 # Command timeout in seconds
    capture_stderr = True        # Include stderr in error messages
    
    def custom_command(self, **kwargs):
        return self._execute("subcommand", **kwargs, response_model=MyModel)
```

#### Response Model Validation

Add Pydantic validators for post-parsing validation:

```python
from pydantic import field_validator

class ValidatedResponse(BaseCLIResponse):
    port: int = Field(pattern=r':(\d+)')
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not 1 <= v <= 65535:
            raise ValueError(f"Port {v} out of valid range")
        return v
```

### Error Handling

#### Structured Error Responses

```python
from clinch import BaseCLIError

class MyToolError(BaseCLIError):
    """Custom error parsing for mytool"""
    error_code: str = Field(pattern=r'ERROR-(\d+)')
    error_message: str = Field(pattern=r'ERROR-\d+: (.+)')

class MyToolWrapper(CLIWrapper):
    command = "mytool"
    error_model = MyToolError  # Use custom error parser
    
    def risky_operation(self):
        try:
            return self._execute("risky", response_model=MyResponse)
        except MyToolError as e:
            print(f"Tool failed: {e.error_code} - {e.error_message}")
            print(f"Exit code: {e.exit_code}")
            print(f"Stderr: {e.stderr}")
```

#### Handling Partial Failures

```python
result = wrapper.get_list_data()

# Separate successes and failures
if result.failures:
    print(f"Parsed {len(result.successes)} items successfully")
    print(f"Failed to parse {len(result.failures)} items")
    
    # Inspect failures
    for failure in result.failures:
        print(f"Failed line: {failure.raw_text}")
        print(f"Attempted patterns: {failure.attempted_patterns}")
        print(f"Error: {failure.exception}")
        
        # Optionally retry with adjusted pattern
        retry_result = failure.retry_with_pattern(r'alternative-(\w+)')
```

## API Reference

### Classes

#### BaseCLIResponse
Base Pydantic model for single CLI output results.

**Usage Pattern:**
```python
class MyResponse(BaseCLIResponse):
    field1: str = Field(pattern=r'pattern1: (\w+)')
    field2: int = Field(pattern=r'count: (\d+)')
```

**Key Features:**
- Inherits from `pydantic.BaseModel`
- Define regex patterns via `Field(pattern=...)`
- Automatic parsing from stdout
- Full Pydantic validation support

**Methods:**
- `parse_output(stdout: str) -> MyResponse`: Class method to parse CLI output

---

#### BaseCLIListResponse
Base Pydantic model for parsing multiple results from CLI output.

**Usage Pattern:**
```python
class LogEntry(BaseCLIListResponse):
    timestamp: str = Field(pattern=r'^\[([^\]]+)\]')
    level: str = Field(pattern=r'\[([A-Z]+)\]')
    message: str = Field(pattern=r'\]\s+(.+)$')
```

**Key Features:**
- Extracts ALL matches from output (not just first)
- Returns `ParsingResult` with successes and failures
- Tracks which lines failed to parse

**Methods:**
- `parse_output(stdout: str) -> ParsingResult`: Class method returning parsed results

---

#### BaseCLIError
Base Pydantic model for CLI error information.

**Fields:**
- `exit_code` (int): Command exit code
- `stderr` (str): Standard error output
- `stdout` (str): Standard output (may be empty)
- `command` (str): The command that was executed

**Usage Pattern:**
```python
class CustomError(BaseCLIError):
    error_type: str = Field(pattern=r'ERROR: (\w+)')
    details: str = Field(pattern=r'Details: (.+)')
```

**Behavior:**
- Automatically raised on non-zero exit codes
- Can be extended to parse structured errors from stderr
- Access raw stderr with `error.stderr`

---

#### CLIWrapper
Base class for creating tool-specific CLI wrappers.

**Class Attributes:**
- `command` (str): **Required.** CLI command name (e.g., "git", "docker")
- `strict_mode` (bool): Raise exception on parsing failures (default: False)
- `timeout` (int): Command timeout in seconds (default: None)
- `error_model` (Type[BaseCLIError]): Custom error model class (default: BaseCLIError)

**Methods:**

##### `_execute(subcommand: str, *args, response_model: Type[T], **kwargs) -> T`
Execute CLI command and parse output.

**Parameters:**
- `subcommand` (str): CLI subcommand (e.g., "branch", "ps")
- `*args`: Positional arguments passed to CLI
- `response_model`: Pydantic model class for parsing output
- `**kwargs`: Converted to CLI flags (e.g., `limit=10` → `--limit 10`)

**Returns:** Instance of `response_model` or `ParsingResult` for list responses

**Raises:** 
- `BaseCLIError` (or custom error_model): On non-zero exit code
- `ParsingError`: On parsing failures (if strict_mode=True)

**Example:**
```python
class GitWrapper(CLIWrapper):
    command = "git"
    
    def log(self, max_count: int = 10) -> list[GitCommit]:
        return self._execute(
            "log", 
            "--oneline",
            max_count=max_count,
            response_model=GitCommit
        )
```

##### `_build_args(**kwargs) -> list[str]`
Override to customize argument formatting.

**Default Behavior:**
- `key=value` → `["--key", "value"]`
- `underscore_key=value` → `["--underscore-key", "value"]`
- `flag=True` → `["--flag"]`
- `flag=False` → (omitted)

**Example Override:**
```python
def _build_args(self, **kwargs) -> list[str]:
    return [f"--{k}={v}" for k, v in kwargs.items()]
```

---

#### ParsingResult
Container for parsing results with success/failure tracking.

**Fields:**
- `successes` (list[T]): Successfully parsed model instances
- `failures` (list[ParsingFailure]): Lines that failed to parse

**Properties:**
- `has_failures` (bool): True if any parsing failures occurred
- `success_count` (int): Number of successful parses
- `failure_count` (int): Number of failed parses

**Example:**
```python
result = wrapper.list_items()
print(f"Parsed {result.success_count}/{result.success_count + result.failure_count}")

for item in result.successes:
    process(item)

if result.has_failures:
    for failure in result.failures:
        log_error(failure.raw_text)
```

---

#### ParsingFailure
Details about a single parsing failure.

**Fields:**
- `raw_text` (str): The original line that failed to parse
- `attempted_patterns` (list[str]): Regex patterns that were tried
- `exception` (Optional[Exception]): The exception that occurred
- `line_number` (int): Line number in output (1-indexed)

**Methods:**
- `retry_with_pattern(pattern: str) -> Optional[T]`: Retry parsing with alternative pattern

**Example:**
```python
for failure in result.failures:
    print(f"Line {failure.line_number}: {failure.raw_text}")
    print(f"Patterns tried: {failure.attempted_patterns}")
    
    # Try alternative parsing
    if "alternative format" in failure.raw_text:
        recovered = failure.retry_with_pattern(r'alt: (\w+)')
        if recovered:
            print(f"Recovered: {recovered}")
```

---

### Utility Functions

#### regex_helpers

Common regex patterns for CLI output parsing.

**Available Patterns:**
- `ISO_DATETIME`: Matches ISO 8601 datetime strings
- `EMAIL`: Matches email addresses
- `IPV4`: Matches IPv4 addresses
- `IPV6`: Matches IPv6 addresses
- `URL`: Matches HTTP/HTTPS URLs
- `UUID`: Matches UUIDs
- `SEMVER`: Matches semantic version strings (e.g., "1.2.3")
- `HEX_COLOR`: Matches hex color codes
- `FILE_PATH`: Matches Unix file paths

**Example:**
```python
from clinch.utils import regex_helpers

class ServerLog(BaseCLIListResponse):
    timestamp: str = Field(pattern=regex_helpers.ISO_DATETIME)
    client_ip: str = Field(pattern=regex_helpers.IPV4)
    url: str = Field(pattern=regex_helpers.URL)
```

## Architecture

### Overview

CLInch uses a layered architecture centered around Pydantic models:

```
┌─────────────────────────────────────┐
│   User's Wrapper Class              │
│   (inherits CLIWrapper)             │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   CLIWrapper Base Class             │
│   - Command execution (_execute)    │
│   - Argument building               │
│   - Error handling                  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   sh Library Integration            │
│   - Process spawning                │
│   - stdout/stderr capture           │
│   - Exit code handling              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   Parsing Engine                    │
│   - Extract Field patterns          │
│   - Apply regex to output           │
│   - Create model instances          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   Pydantic Validation               │
│   - Type coercion                   │
│   - Field validation                │
│   - Model creation                  │
└─────────────────────────────────────┘
```

**Key Components:**
- **User Wrappers**: Inherit from `CLIWrapper`, define tool-specific methods
- **Base Models**: `BaseCLIResponse` and `BaseCLIListResponse` for output structure
- **Parsing Engine**: Extracts regex patterns from Pydantic Field metadata
- **Result Tracking**: `ParsingResult` separates successes from failures

### Data Flow

**Single Result Flow:**
1. User calls wrapper method (e.g., `git.status()`)
2. `CLIWrapper._execute()` builds command arguments
3. `sh` library executes command, captures output
4. Exit code checked → non-zero raises error
5. Parsing engine extracts patterns from response model
6. Regex applied to stdout
7. Pydantic validates and creates model instance
8. Model instance returned to user

**List Result Flow:**
1. Similar execution through step 4
2. Parsing engine finds ALL matches in output
3. For each match:
   - Try to create model instance
   - Success → add to `successes` list
   - Failure → create `ParsingFailure`, add to `failures` list
4. Return `ParsingResult` with both lists

**Error Flow:**
1. Non-zero exit code detected
2. If custom `error_model` defined, parse stderr
3. Create error instance with exit code, stderr, stdout
4. Raise as exception
5. User catches and handles

### Extension Points

#### 1. Custom Argument Formatting
Override `_build_args()` to change parameter → CLI arg conversion:

```python
class CustomWrapper(CLIWrapper):
    def _build_args(self, **kwargs) -> list[str]:
        # Single-dash flags instead of double-dash
        return [f"-{k}" for k, v in kwargs.items() if v]
```

#### 2. Custom Parsing Logic
Override `_parse_output()` for non-regex parsing:

```python
class JSONWrapper(CLIWrapper):
    def _parse_output(self, stdout: str, response_model: Type[T]) -> T:
        import json
        data = json.loads(stdout)
        return response_model(**data)
```

#### 3. Custom Error Handling
Define `error_model` for structured error parsing:

```python
class ToolError(BaseCLIError):
    error_id: str = Field(pattern=r'ERR-(\d+)')
    suggestion: str = Field(pattern=r'Try: (.+)')

class ToolWrapper(CLIWrapper):
    command = "mytool"
    error_model = ToolError
```

#### 4. Post-Parsing Validation
Use Pydantic validators in response models:

```python
class ValidatedResponse(BaseCLIResponse):
    value: int = Field(pattern=r'value: (\d+)')
    
    @field_validator('value')
    @classmethod
    def check_range(cls, v: int) -> int:
        if v < 0 or v > 100:
            raise ValueError("Value must be 0-100")
        return v
```

#### 5. Preprocessing Hooks
Override `_preprocess_output()` to clean output before parsing:

```python
class CleanWrapper(CLIWrapper):
    def _preprocess_output(self, stdout: str) -> str:
        # Remove ANSI color codes
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', stdout)
```

### Performance Considerations

**Parsing Complexity:**
- Time: O(n × m) where n = output lines, m = number of Field patterns
- Space: O(n) for storing matches and failures
- Regex compilation is cached by Python's `re` module

**Optimization Tips:**
1. **Minimize Patterns**: Fewer Field patterns = faster parsing
2. **Specific Regexes**: More specific patterns reduce backtracking
3. **Streaming (Future)**: For very large outputs, consider streaming parser
4. **Batch Operations**: Single CLI call is cheaper than multiple calls

**Overhead:**
- ~1-5ms added to command execution time for parsing
- Negligible compared to actual CLI execution time
- Pydantic validation overhead is minimal for simple models

**Memory Usage:**
- Each parsed instance: ~1KB + field data size
- Failed parses stored as lightweight `ParsingFailure` objects
- Large outputs (1000+ lines) use ~1-2MB RAM

## Examples

### Use Case 1: Wrapping Jujutsu (jj) Version Control

```python
from clinch import CLIWrapper, BaseCLIListResponse, BaseCLIResponse
from pydantic import Field
from clinch.utils import regex_helpers

class RawOutput(BaseCLIResponse):
    """Helper for commands that return unstructured text"""
    text: str = Field(pattern=r'(.*)', default="")

class JujutsuCommit(BaseCLIListResponse):
    """Single commit from jj log output"""
    change_id: str = Field(pattern=r'@\s+([a-z0-9]+)')
    author: str = Field(pattern=regex_helpers.EMAIL)
    timestamp: str = Field(pattern=regex_helpers.ISO_DATETIME)
    description: str = Field(pattern=r'\(empty\)\s+(.+)')
    
class JujutsuWrapper(CLIWrapper):
    command = "jj"
    
    def log(self, limit: int = 10, revisions: str = "all()") -> list[JujutsuCommit]:
        """Get commit log with optional filtering"""
        return self._execute(
            "log",
            limit=limit,
            revisions=revisions,
            response_model=JujutsuCommit
        )
    
    def status(self) -> str:
        """Get working copy status (returns raw output)"""
        result = self._execute("status", response_model=RawOutput)
        return result.text

# Usage
jj = JujutsuWrapper()
commits = jj.log(limit=5, revisions="main..@")

for commit in commits.successes:
    print(f"{commit.change_id[:12]} - {commit.author}")
    print(f"  {commit.description}")
    print(f"  {commit.timestamp}\n")

# Check for parsing issues
if commits.has_failures:
    print(f"Warning: {commits.failure_count} commits failed to parse")
    for failure in commits.failures:
        print(f"  Line {failure.line_number}: {failure.raw_text[:50]}...")
```

### Use Case 2: GitHub CLI Integration

```python
from clinch import CLIWrapper, BaseCLIListResponse, BaseCLIError
from pydantic import Field, field_validator

class GitHubPR(BaseCLIListResponse):
    """Pull request from gh pr list"""
    number: int = Field(pattern=r'#(\d+)')
    title: str = Field(pattern=r'#\d+\s+(.+?)\s+[A-Z]+')
    state: str = Field(pattern=r'\s+(OPEN|CLOSED|MERGED)\s+')
    author: str = Field(pattern=r'by\s+(\S+)')
    
    @field_validator('state')
    @classmethod
    def uppercase_state(cls, v: str) -> str:
        return v.upper()

class GitHubError(BaseCLIError):
    """Parse GitHub CLI errors"""
    error_type: str = Field(pattern=r'(\w+Error):')
    message: str = Field(pattern=r'\w+Error:\s+(.+)')

class GitHubWrapper(CLIWrapper):
    command = "gh"
    error_model = GitHubError
    timeout = 30  # API calls might be slow
    
    def pr_list(self, state: str = "open", limit: int = 10) -> list[GitHubPR]:
        """List pull requests"""
        return self._execute(
            "pr", "list",
            state=state,
            limit=limit,
            response_model=GitHubPR
        )
    
    def pr_create(self, title: str, body: str, draft: bool = False) -> str:
        """Create a pull request"""
        args = ["pr", "create", "--title", title, "--body", body]
        if draft:
            args.append("--draft")
        return self._execute(*args, response_model=RawOutput).text

# Usage
gh = GitHubWrapper()

try:
    prs = gh.pr_list(state="open", limit=5)
    for pr in prs.successes:
        status_icon = "🟢" if pr.state == "OPEN" else "🔴"
        print(f"{status_icon} #{pr.number}: {pr.title}")
        print(f"   by {pr.author}\n")
except GitHubError as e:
    print(f"GitHub CLI error: {e.error_type}")
    print(f"Message: {e.message}")
    print(f"Run 'gh auth login' if not authenticated")
```

### Use Case 3: Docker Container Management

```python
from clinch import CLIWrapper, BaseCLIListResponse, BaseCLIResponse
from pydantic import Field
from typing import Optional

class DockerContainer(BaseCLIListResponse):
    """Parse docker ps output"""
    container_id: str = Field(pattern=r'^([a-f0-9]{12})')
    image: str = Field(pattern=r'[a-f0-9]{12}\s+(\S+)')
    command: str = Field(pattern=r'"\s*(.+?)\s*"')
    status: str = Field(pattern=r'(Up|Exited)\s+[^/]+')
    ports: Optional[str] = Field(default=None, pattern=r'(\d+:\d+/tcp)')
    name: str = Field(pattern=r'\s+(\S+)$')

class DockerInspect(BaseCLIResponse):
    """Parse docker inspect for specific fields"""
    ip_address: str = Field(pattern=r'"IPAddress":\s*"([^"]+)"')
    gateway: str = Field(pattern=r'"Gateway":\s*"([^"]+)"')

class DockerWrapper(CLIWrapper):
    command = "docker"
    strict_mode = False  # Some containers may not match all patterns
    
    def ps(self, all_containers: bool = False) -> list[DockerContainer]:
        """List containers"""
        return self._execute(
            "ps",
            all=all_containers if all_containers else None,
            response_model=DockerContainer
        )
    
    def inspect(self, container_id: str) -> DockerInspect:
        """Get container network details"""
        return self._execute(
            "inspect",
            container_id,
            response_model=DockerInspect
        )
    
    def _build_args(self, **kwargs) -> list[str]:
        """Custom arg builder for docker's flag style"""
        args = []
        for key, value in kwargs.items():
            if value is None:
                continue
            flag = f"--{key.replace('_', '-')}"
            if isinstance(value, bool):
                if value:
                    args.append(flag)
            else:
                args.extend([flag, str(value)])
        return args

# Usage
docker = DockerWrapper()

# List running containers
containers = docker.ps()
print(f"Running containers: {len(containers.successes)}\n")

for container in containers.successes:
    print(f"📦 {container.name} ({container.container_id})")
    print(f"   Image: {container.image}")
    print(f"   Status: {container.status}")
    
    # Get network details
    if container.status.startswith("Up"):
        details = docker.inspect(container.container_id)
        print(f"   IP: {details.ip_address}")
    print()
```

### Use Case 4: System Monitoring with ps/top

```python
from clinch import CLIWrapper, BaseCLIListResponse
from pydantic import Field, field_validator
from typing import Optional

class ProcessInfo(BaseCLIListResponse):
    """Parse ps aux output"""
    user: str = Field(pattern=r'^(\S+)')
    pid: int = Field(pattern=r'^\S+\s+(\d+)')
    cpu_percent: float = Field(pattern=r'(\d+\.\d+)%')
    mem_percent: float = Field(pattern=r'\d+\.\d+\s+(\d+\.\d+)')
    vsz: int = Field(pattern=r'\d+\.\d+\s+\d+\.\d+\s+(\d+)')
    command: str = Field(pattern=r'\s+(\S+)$')
    
    @field_validator('cpu_percent', 'mem_percent')
    @classmethod
    def clamp_percentage(cls, v: float) -> float:
        """Ensure percentages are in valid range"""
        return max(0.0, min(100.0, v))

class SystemWrapper(CLIWrapper):
    command = "ps"
    strict_mode = True  # We expect all lines to parse
    
    def top_cpu(self, limit: int = 10) -> list[ProcessInfo]:
        """Get top CPU-consuming processes"""
        result = self._execute("aux", response_model=ProcessInfo)
        
        # Sort by CPU usage (post-processing)
        sorted_procs = sorted(
            result.successes,
            key=lambda p: p.cpu_percent,
            reverse=True
        )
        return sorted_procs[:limit]
    
    def top_memory(self, limit: int = 10) -> list[ProcessInfo]:
        """Get top memory-consuming processes"""
        result = self._execute("aux", response_model=ProcessInfo)
        
        sorted_procs = sorted(
            result.successes,
            key=lambda p: p.mem_percent,
            reverse=True
        )
        return sorted_procs[:limit]

# Usage
system = SystemWrapper()

print("🔥 Top 5 CPU consumers:")
for proc in system.top_cpu(limit=5):
    print(f"  {proc.cpu_percent:5.1f}% - PID {proc.pid:6} - {proc.command}")

print("\n💾 Top 5 Memory consumers:")
for proc in system.top_memory(limit=5):
    mem_mb = proc.vsz / 1024  # Convert KB to MB
    print(f"  {proc.mem_percent:5.1f}% ({mem_mb:7.1f}MB) - {proc.command}")
```

### Integration Examples

#### Using with Pytest for Testing

```python
import pytest
from my_wrappers import GitWrapper, GitCommit

@pytest.fixture
def git():
    return GitWrapper()

def test_git_log_parsing(git):
    """Test that git log parses correctly"""
    result = git.log(limit=5)
    
    assert result.success_count > 0, "Should parse at least one commit"
    assert result.failure_count == 0, "Should parse all commits successfully"
    
    for commit in result.successes:
        assert commit.hash, "Commit hash should not be empty"
        assert commit.author, "Author should not be empty"
        assert '@' in commit.author, "Author should be email format"

def test_error_handling(git):
    """Test that invalid commands raise proper errors"""
    with pytest.raises(BaseCLIError) as exc_info:
        git._execute("invalid-subcommand", response_model=GitCommit)
    
    assert exc_info.value.exit_code != 0
    assert "invalid" in exc_info.value.stderr.lower()
```

#### Integration with Rich for Pretty Output

```python
from rich.console import Console
from rich.table import Table
from my_wrappers import DockerWrapper

console = Console()
docker = DockerWrapper()

# Create a rich table from parsed data
table = Table(title="Docker Containers")
table.add_column("Name", style="cyan")
table.add_column("Image", style="magenta")
table.add_column("Status", style="green")
table.add_column("Ports", style="yellow")

containers = docker.ps()
for container in containers.successes:
    table.add_row(
        container.name,
        container.image,
        container.status,
        container.ports or "—"
    )

console.print(table)
```

#### Building a CLI Tool with Typer

```python
import typer
from my_wrappers import JujutsuWrapper

app = typer.Typer()
jj = JujutsuWrapper()

@app.command()
def log(
    limit: int = typer.Option(10, help="Number of commits to show"),
    revisions: str = typer.Option("all()", help="Revision query")
):
    """Show jujutsu commit log"""
    result = jj.log(limit=limit, revisions=revisions)
    
    for commit in result.successes:
        typer.echo(f"{commit.change_id[:12]} - {commit.description}")
    
    if result.has_failures:
        typer.secho(
            f"\nWarning: {result.failure_count} commits failed to parse",
            fg=typer.colors.YELLOW
        )

if __name__ == "__main__":
    app()
```

## Development

### Project Structure
```
clinch/
├── src/clinch/
│   ├── __init__.py
│   ├── base/
│   │   ├── __init__.py
│   │   ├── response.py
│   │   ├── error.py
│   │   └── wrapper.py
│   ├── parsing/
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   └── result.py
│   └── utils/
│       ├── __init__.py
│       └── regex_helpers.py
├── tests/
├── docs/
├── pyproject.toml
└── README.md
```

### Running Tests
```bash
uv run pytest
```

### Code Quality
```bash
uv run ruff check
uv run ruff format
uv run mypy src/
```

### Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests and quality checks pass
5. Submit a pull request

## Technical Specifications

### Requirements
- Python 3.13+
- pydantic >= 2.10
- sh >= 2.0

### Performance
- Parsing complexity: O(n*m) where n=output lines, m=regex patterns
- Minimal overhead compared to direct `sh` library usage

### Compatibility
- Unix-like systems (Linux, macOS)
- Python 3.13+
- Any CLI tool accessible via the `sh` library
- Full mypy and pyright type checking support

### Limitations
- Does not support interactive CLI tools (requiring stdin interaction)
- Does not parse binary output
- Regex-based parsing only (no XML/YAML in v0.1.0)
- Synchronous execution only (no async support in v0.1.0)

## FAQ

### How is CLInch different from subprocess or sh?
CLInch builds on top of `sh` but adds type safety through Pydantic models and declarative parsing. Instead of manually parsing CLI output with string operations, you define the expected structure once and get validated Python objects.

### Do I need to know regex?
Basic regex knowledge helps, but the `regex_helpers` module provides common patterns. For simple extractions, patterns like `r'name: (\w+)'` are straightforward. Complex tools may require more sophisticated patterns.

### What if a CLI tool changes its output format?
Update your response model's Field patterns. If you have tests, they'll catch breaking changes. CLInch's partial failure tracking helps identify which patterns need adjustment.

### Can I use this with Windows CLI tools?
The `sh` library is Unix-focused. For Windows, consider using `subprocess` directly or contributing Windows support to CLInch.

### Should I create wrappers for all my CLI tools?
Start with tools you call frequently or where type safety adds value. Quick scripts may not need wrappers, but production code benefits from CLInch's structure.

### How do I handle commands with subcommands?
Pass subcommands as positional arguments to `_execute()`:
```python
def pr_list(self):
    return self._execute("pr", "list", response_model=PRModel)
```

### Can I use custom validation beyond regex?
Yes! Add Pydantic `@field_validator` decorators to your response models for post-parsing validation.

## Roadmap

### v0.2.0 (Planned)
- Async/await support for concurrent CLI operations
- Streaming output parser for long-running commands
- Additional output formats (YAML, XML)
- Performance optimizations for large outputs

### v0.3.0 (Future)
- Shell script generation from wrapper calls
- Interactive CLI tool support
- Plugin system for custom parsers
- CLI wrapper generator tool

### Community Extensions
Consider creating these as separate packages:
- `clinch-tools`: Pre-built wrappers for popular tools (jj, gh, docker, kubectl)
- `clinch-plugins`: Alternative parsing backends and utilities

## License

MIT License - see LICENSE file for details.
