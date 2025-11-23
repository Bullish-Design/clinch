# SPEC.md
# CLInch Technical Specification

## Document Information

* **Version:** 0.1.0
* **Last Updated:** 2024-11-22
* **Status:** Draft

## Executive Summary

CLInch is a Pydantic-based library for wrapping Unix CLI tools with type-safe Python interfaces. It uses declarative regex patterns in Pydantic Field metadata to parse CLI output into validated Python objects, eliminating manual string parsing boilerplate while providing comprehensive error handling and partial failure tracking.

## Requirements

### Functional Requirements

#### Core Features

**REQ-001: CLI Command Execution**

* **Description:** Execute arbitrary CLI commands through Python wrapper classes and capture stdout/stderr
* **Inputs:** 
  - Command name (string)
  - Subcommands (variable positional strings)
  - Keyword arguments (converted to CLI flags)
* **Outputs:** Raw stdout/stderr strings and exit code
* **Priority:** Critical
* **Acceptance Criteria:**
  * [ ] Execute commands using sh library
  * [ ] Capture stdout, stderr, and exit code
  * [ ] Support timeout configuration
  * [ ] Handle non-zero exit codes appropriately

**REQ-002: Regex-Based Output Parsing**

* **Description:** Parse CLI output using regex patterns defined in Pydantic Field metadata
* **Inputs:** 
  - Raw stdout string
  - Pydantic model with Field patterns
* **Outputs:** Validated Pydantic model instance(s)
* **Priority:** Critical
* **Acceptance Criteria:**
  * [ ] Extract patterns from Field metadata
  * [ ] Apply regex to stdout
  * [ ] Create model instances from matches
  * [ ] Support multiple patterns per model
  * [ ] Handle optional fields gracefully

**REQ-003: Partial Failure Tracking**

* **Description:** Track successful and failed parsing attempts separately
* **Inputs:** CLI output with mixed parseable/unparseable lines
* **Outputs:** ParsingResult container with successes and failures
* **Priority:** Critical
* **Acceptance Criteria:**
  * [ ] Separate successful parses into successes list
  * [ ] Capture failed lines with failure details
  * [ ] Provide failure metadata (line number, attempted patterns, exception)
  * [ ] Allow retry of failed parses with alternative patterns

**REQ-004: Structured Error Handling**

* **Description:** Parse CLI errors into typed exception objects
* **Inputs:** Non-zero exit code, stderr output
* **Outputs:** BaseCLIError or custom error model instance
* **Priority:** High
* **Acceptance Criteria:**
  * [ ] Raise exceptions on non-zero exit codes
  * [ ] Parse stderr using error_model if defined
  * [ ] Include exit code, stderr, stdout in error
  * [ ] Support custom error model classes

**REQ-005: Argument Formatting**

* **Description:** Convert Python kwargs to CLI arguments
* **Inputs:** Keyword arguments with various types (bool, int, str, etc.)
* **Outputs:** List of CLI argument strings
* **Priority:** High
* **Acceptance Criteria:**
  * [ ] Convert underscore_key to --underscore-key
  * [ ] Handle boolean flags (True → --flag, False → omit)
  * [ ] Convert values to strings appropriately
  * [ ] Support override via _build_args()

#### Extended Features

**REQ-006: Output Preprocessing**

* **Description:** Allow custom preprocessing of stdout before parsing
* **Priority:** Medium
* **Dependencies:** REQ-001, REQ-002
* **Acceptance Criteria:**
  * [ ] Provide _preprocess_output() hook
  * [ ] Apply before pattern extraction
  * [ ] Support common transformations (ANSI removal, etc.)

**REQ-007: Regex Helper Library**

* **Description:** Provide common regex patterns for CLI parsing
* **Priority:** Medium
* **Dependencies:** REQ-002
* **Acceptance Criteria:**
  * [ ] Include patterns for ISO datetime, email, IPv4/6, URLs, UUIDs, semver
  * [ ] Patterns accessible via regex_helpers module
  * [ ] Patterns tested and documented

**REQ-008: Strict Parsing Mode**

* **Description:** Optionally raise exceptions on any parsing failure
* **Priority:** Medium
* **Dependencies:** REQ-003
* **Acceptance Criteria:**
  * [ ] Configurable via strict_mode class attribute
  * [ ] Raise on first parsing failure when enabled
  * [ ] Default to False for permissive behavior

## Architecture

### System Overview

```
┌────────────────────────────────────────────────────────────┐
│                    User Wrapper Class                      │
│                  (inherits CLIWrapper)                     │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ def custom_method(self, **kwargs):                   │ │
│  │     return self._execute("subcommand",               │ │
│  │                         response_model=MyModel)      │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────┬──────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────┐
│                    CLIWrapper Base                         │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ _execute(subcommand, *args, **kwargs)                │ │
│  │   1. Build CLI args via _build_args()                │ │
│  │   2. Execute via sh library                          │ │
│  │   3. Check exit code → raise error if non-zero       │ │
│  │   4. Preprocess output via _preprocess_output()      │ │
│  │   5. Parse via ParsingEngine                         │ │
│  │   6. Return ParsingResult[T]                         │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────┬──────────────────────────────────┘
                          │
            ┌─────────────┼─────────────┐
            │             │             │
            ▼             ▼             ▼
    ┌──────────┐   ┌───────────┐   ┌────────────┐
    │    sh    │   │  Parsing  │   │   Error    │
    │  Library │   │  Engine   │   │  Handler   │
    └──────────┘   └───────────┘   └────────────┘
         │              │                 │
         │              │                 │
         ▼              ▼                 ▼
    Execute CLI    Extract Field     Parse stderr
    Capture I/O    Apply Regex       Create Error
    Return Code    Validate Model    Raise Exception
```

### Core Components

#### Class Hierarchy

```python
# src/clinch/base/response.py
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any, ClassVar

class BaseCLIResponse(BaseModel):
    """Base Pydantic model for CLI output parsing.
    
    Subclasses define fields with pattern metadata for regex extraction.
    """
    
    # Class-level registry of field patterns (populated at model creation)
    _field_patterns: ClassVar[dict[str, str]] = {}
    
    @classmethod
    def model_post_init(cls, __context: Any) -> None:
        """Extract patterns from Field metadata on model creation."""
        # Implementation extracts Field(pattern=...) metadata
        pass
    
    @classmethod
    def parse_output(cls, stdout: str) -> ParsingResult[BaseCLIResponse]:
        """Parse CLI output into model instance(s).
        
        Args:
            stdout: Raw CLI output string
            
        Returns:
            ParsingResult with successfully parsed instances and failures
        """
        pass


# src/clinch/base/error.py
from __future__ import annotations
from pydantic import BaseModel, Field

class BaseCLIError(BaseModel, Exception):
    """Base exception for CLI execution errors.
    
    Contains structured error information from failed CLI commands.
    """
    exit_code: int = Field(description="Command exit code")
    stderr: str = Field(description="Standard error output")
    stdout: str = Field(default="", description="Standard output (may be empty)")
    command: str = Field(description="The executed command")
    
    def __str__(self) -> str:
        """Format error message for display."""
        return f"Command '{self.command}' failed with exit code {self.exit_code}: {self.stderr}"


# src/clinch/base/wrapper.py
from __future__ import annotations
from typing import TypeVar, Type, Any
from pydantic import BaseModel

T = TypeVar('T', bound=BaseCLIResponse)

class CLIWrapper:
    """Base class for CLI tool wrappers.
    
    Subclasses define command and tool-specific methods.
    """
    
    # Required: CLI command name
    command: str
    
    # Optional configuration
    strict_mode: bool = False
    timeout: int | None = None
    error_model: Type[BaseCLIError] = BaseCLIError
    
    def _execute(
        self,
        subcommand: str,
        *args: str,
        response_model: Type[T],
        **kwargs: Any
    ) -> ParsingResult[T]:
        """Execute CLI command and parse output.
        
        Args:
            subcommand: CLI subcommand to execute
            *args: Additional positional arguments
            response_model: Pydantic model for output parsing
            **kwargs: Keyword arguments converted to CLI flags
            
        Returns:
            ParsingResult containing parsed instances and failures
            
        Raises:
            BaseCLIError: On non-zero exit code
            ParsingError: On parsing failure (if strict_mode=True)
        """
        pass
    
    def _build_args(self, **kwargs: Any) -> list[str]:
        """Convert kwargs to CLI arguments.
        
        Default behavior:
            underscore_key=value → ["--underscore-key", "value"]
            flag=True → ["--flag"]
            flag=False → []
            
        Override for custom argument formatting.
        """
        pass
    
    def _preprocess_output(self, stdout: str) -> str:
        """Preprocess stdout before parsing.
        
        Override to strip ANSI codes, normalize whitespace, etc.
        Default implementation returns stdout unchanged.
        """
        return stdout
```

#### Component Responsibilities

* **CLIWrapper**: Command execution orchestration, argument building, error handling
* **BaseCLIResponse**: Pydantic model definition, pattern storage, parsing coordination
* **BaseCLIError**: Structured error information and exception behavior
* **ParsingEngine**: Pattern extraction, regex application, model instantiation
* **ParsingResult**: Success/failure tracking, result aggregation
* **ParsingFailure**: Failure metadata and retry mechanism

#### Data Flow

1. **User invokes wrapper method**
   - Example: `git.branch(limit=10)`
   
2. **Method calls _execute()**
   - Passes subcommand, kwargs, and response_model
   
3. **Argument building**
   - `_build_args()` converts kwargs to CLI args: `["--limit", "10"]`
   - Full command assembled: `["git", "branch", "--limit", "10"]`
   
4. **Command execution via sh**
   - `sh.Command(command)(subcommand, *args, *cli_args)`
   - Captures stdout, stderr, exit_code
   
5. **Exit code check**
   - If non-zero: parse stderr with error_model, raise exception
   - If zero: continue to parsing
   
6. **Output preprocessing**
   - `_preprocess_output(stdout)` applies transformations
   
7. **Parsing**
   - Extract Field patterns from response_model
   - Apply regexes to stdout (line-by-line or full text)
   - For each match attempt:
     - Success: create model instance, add to successes
     - Failure: create ParsingFailure, add to failures
   
8. **Strict mode check**
   - If strict_mode and failures exist: raise ParsingError
   
9. **Return ParsingResult**
   - Contains `.successes` and `.failures` lists

### Design Patterns

* **Template Method**: `_execute()` defines skeleton, `_build_args()` and `_preprocess_output()` as hooks
* **Factory Pattern**: Response models create instances from parsed data
* **Strategy Pattern**: Configurable error_model allows custom error parsing
* **Metadata Pattern**: Field patterns stored in Pydantic metadata, extracted at runtime

## Data Structures

### Input/Output Schemas

```python
# src/clinch/parsing/result.py
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Generic, TypeVar

T = TypeVar('T', bound=BaseCLIResponse)

class ParsingFailure(BaseModel):
    """Details about a single parsing failure."""
    
    raw_text: str = Field(description="Original line that failed to parse")
    attempted_patterns: list[str] = Field(description="Regex patterns that were tried")
    exception: str | None = Field(default=None, description="Exception message if any")
    line_number: int = Field(description="Line number in output (1-indexed)")
    
    def retry_with_pattern(self, pattern: str) -> T | None:
        """Retry parsing with alternative pattern.
        
        Args:
            pattern: Alternative regex pattern to try
            
        Returns:
            Parsed model instance if successful, None otherwise
        """
        pass


class ParsingResult(BaseModel, Generic[T]):
    """Container for parsing results with success/failure tracking."""
    
    successes: list[T] = Field(default_factory=list, description="Successfully parsed instances")
    failures: list[ParsingFailure] = Field(default_factory=list, description="Failed parsing attempts")
    
    @property
    def has_failures(self) -> bool:
        """True if any parsing failures occurred."""
        return len(self.failures) > 0
    
    @property
    def success_count(self) -> int:
        """Number of successful parses."""
        return len(self.successes)
    
    @property
    def failure_count(self) -> int:
        """Number of failed parses."""
        return len(self.failures)
```

### Internal Data Models

```python
# src/clinch/fields.py
from __future__ import annotations
from pydantic import Field as PydanticField
from pydantic_core import PydanticUndefined
from typing import Any

def Field(
    default: Any = PydanticUndefined,
    *,
    pattern: str | None = None,
    **kwargs: Any
) -> Any:
    """Custom Field wrapper that stores regex pattern in metadata.
    
    Args:
        default: Default value for field
        pattern: Regex pattern for extraction (stored in json_schema_extra)
        **kwargs: Other Pydantic Field arguments
        
    Returns:
        Pydantic FieldInfo with pattern in metadata
    """
    json_schema_extra = kwargs.pop('json_schema_extra', {})
    if pattern is not None:
        json_schema_extra['pattern'] = pattern
    
    return PydanticField(default, json_schema_extra=json_schema_extra, **kwargs)
```

### Validation Rules

* **Pattern Extraction**: Patterns must be valid Python regex strings
* **Model Creation**: All required fields without patterns must have defaults
* **Exit Code**: Must be integer, typically 0 for success
* **Timeout**: Must be positive integer or None
* **Command**: Must be non-empty string

## API Specification

### Public Interface

```python
# Main exports from src/clinch/__init__.py
from clinch.base.wrapper import CLIWrapper
from clinch.base.response import BaseCLIResponse
from clinch.base.error import BaseCLIError
from clinch.parsing.result import ParsingResult, ParsingFailure
from clinch.fields import Field

__all__ = [
    'CLIWrapper',
    'BaseCLIResponse',
    'BaseCLIError',
    'ParsingResult',
    'ParsingFailure',
    'Field',
]
```

### Configuration

```python
# Wrapper configuration via class attributes
class MyToolWrapper(CLIWrapper):
    command = "mytool"              # Required
    strict_mode = False             # Raise on parsing failures
    timeout = 30                    # Command timeout in seconds
    error_model = CustomError       # Custom error parsing class
```

### Usage Examples

```python
# Basic usage
from clinch import CLIWrapper, BaseCLIResponse, Field

class GitBranch(BaseCLIResponse):
    name: str = Field(pattern=r'\*?\s+(\S+)')
    is_current: bool = Field(default=False, pattern=r'(\*)')

class GitWrapper(CLIWrapper):
    command = "git"
    
    def branch(self) -> ParsingResult[GitBranch]:
        return self._execute("branch", response_model=GitBranch)

git = GitWrapper()
result = git.branch()

for branch in result.successes:
    print(f"{'→' if branch.is_current else ' '} {branch.name}")

# Advanced usage with error handling
from clinch import BaseCLIError

class MyToolError(BaseCLIError):
    error_code: str = Field(pattern=r'ERR-(\d+)')

class MyToolWrapper(CLIWrapper):
    command = "mytool"
    error_model = MyToolError
    
    def risky_operation(self, verbose: bool = False):
        try:
            return self._execute("risky", verbose=verbose, response_model=MyResponse)
        except MyToolError as e:
            print(f"Error {e.error_code}: {e.stderr}")
```

## Error Handling

### Exception Hierarchy

```python
# src/clinch/exceptions.py
from __future__ import annotations

class CLInchException(Exception):
    """Base exception for all CLInch errors."""
    pass


class ParsingError(CLInchException):
    """Raised when parsing fails in strict mode."""
    
    def __init__(self, failures: list[ParsingFailure]):
        self.failures = failures
        super().__init__(
            f"Failed to parse {len(failures)} line(s). "
            f"First failure: {failures[0].raw_text[:50]}..."
        )


class CommandNotFoundError(CLInchException):
    """Raised when CLI command doesn't exist."""
    pass


class TimeoutError(CLInchException):
    """Raised when command execution times out."""
    pass
```

### Error Scenarios

* **Invalid Input**: Pydantic validation errors raised for malformed kwargs
* **Command Not Found**: Raised when sh cannot find command (via sh.CommandNotFound)
* **Non-zero Exit Code**: Raises error_model instance (default BaseCLIError)
* **Parsing Failure (strict mode)**: Raises ParsingError with all failures
* **Timeout**: Raises TimeoutError if command exceeds timeout

### Error Messages

* Include context: command, exit code, stderr excerpt
* Actionable suggestions: "Run 'gh auth login'" for auth errors
* Structured format: "Command 'X' failed with exit code Y: <stderr>"
* Parsing errors: Include line number, attempted patterns, first failure example

## Dependencies

### Core Dependencies

```toml
# pyproject.toml
[project]
name = "clinch"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "pydantic>=2.10",
    "sh>=2.0",
]
```

### Optional Dependencies

None in v0.1.0

### Development Dependencies

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
    "ruff>=0.1",
    "mypy>=1.8",
]
```

## Testing Strategy

### Unit Tests

```python
# tests/test_parsing.py
import pytest
from clinch import BaseCLIResponse, Field, ParsingResult

class TestResponse(BaseCLIResponse):
    value: str = Field(pattern=r'value: (\w+)')

def test_parse_single_line():
    """Test parsing single line output."""
    result = TestResponse.parse_output("value: hello")
    
    assert result.success_count == 1
    assert result.successes[0].value == "hello"
    assert result.failure_count == 0

def test_parse_multiple_lines():
    """Test parsing multiple lines."""
    output = "value: first\nvalue: second\nvalue: third"
    result = TestResponse.parse_output(output)
    
    assert result.success_count == 3
    assert [r.value for r in result.successes] == ["first", "second", "third"]

def test_parse_with_failures():
    """Test partial parsing with some failures."""
    output = "value: good\ninvalid line\nvalue: also_good"
    result = TestResponse.parse_output(output)
    
    assert result.success_count == 2
    assert result.failure_count == 1
    assert result.failures[0].raw_text == "invalid line"

def test_strict_mode_raises():
    """Test strict mode raises on parsing failure."""
    class StrictResponse(BaseCLIResponse):
        value: str = Field(pattern=r'value: (\w+)')
        
    # Implementation would set strict_mode context
    with pytest.raises(ParsingError):
        StrictResponse.parse_output("invalid line")


# tests/test_wrapper.py
import pytest
from clinch import CLIWrapper, BaseCLIResponse, Field

class MockResponse(BaseCLIResponse):
    output: str = Field(pattern=r'(.+)')

class TestWrapper(CLIWrapper):
    command = "echo"

def test_execute_success():
    """Test successful command execution."""
    wrapper = TestWrapper()
    result = wrapper._execute("hello", response_model=MockResponse)
    
    assert result.success_count == 1
    assert result.successes[0].output == "hello"

def test_build_args_conversion():
    """Test kwargs to CLI args conversion."""
    wrapper = TestWrapper()
    args = wrapper._build_args(max_count=10, verbose=True, quiet=False)
    
    assert args == ["--max-count", "10", "--verbose"]

def test_error_handling():
    """Test error on non-zero exit code."""
    # This would use a mock or actual failing command
    pass


# tests/test_fields.py
import pytest
from clinch import Field, BaseCLIResponse

def test_field_stores_pattern():
    """Test Field stores pattern in metadata."""
    class TestModel(BaseCLIResponse):
        value: str = Field(pattern=r'test: (\w+)')
    
    # Verify pattern stored in field metadata
    field_info = TestModel.model_fields['value']
    assert field_info.json_schema_extra['pattern'] == r'test: (\w+)'

def test_field_without_pattern():
    """Test Field works without pattern."""
    class TestModel(BaseCLIResponse):
        value: str = Field(default="default")
    
    field_info = TestModel.model_fields['value']
    assert 'pattern' not in field_info.json_schema_extra
```

### Integration Tests

* **Real CLI Tools**: Test with actual git, docker, etc. commands
* **Error Scenarios**: Test with commands that fail (invalid args, missing tools)
* **Complex Parsing**: Test multi-field models with various output formats
* **Timeout Handling**: Test commands that exceed timeout

### Test Coverage Requirements

* Minimum 90% line coverage
* 100% coverage for:
  - Pattern extraction logic
  - Argument building
  - Error handling paths
  - ParsingResult operations

## Implementation Guidelines

### Code Style

Enforced by Ruff - ignore for specification purposes.

### File Organization

```
clinch/
├── src/clinch/
│   ├── __init__.py                 # Public API exports
│   ├── base/
│   │   ├── __init__.py
│   │   ├── response.py             # BaseCLIResponse
│   │   ├── error.py                # BaseCLIError
│   │   └── wrapper.py              # CLIWrapper
│   ├── parsing/
│   │   ├── __init__.py
│   │   ├── engine.py               # Pattern extraction and regex application
│   │   └── result.py               # ParsingResult, ParsingFailure
│   ├── utils/
│   │   ├── __init__.py
│   │   └── regex_helpers.py        # Common regex patterns
│   ├── fields.py                   # Custom Field wrapper
│   └── exceptions.py               # Exception classes
├── tests/
│   ├── __init__.py
│   ├── test_parsing.py
│   ├── test_wrapper.py
│   ├── test_fields.py
│   ├── test_errors.py
│   └── integration/
│       ├── test_real_tools.py
│       └── test_examples.py
├── docs/
│   ├── index.md
│   ├── quickstart.md
│   ├── api.md
│   └── examples.md
├── pyproject.toml
└── README.md
```

### Development Workflow

1. Create feature branch from main
2. Implement feature with tests (TDD preferred)
3. Run test suite: `uv run pytest`
4. Run type checking: `uv run mypy src/`
5. Run linting: `uv run ruff check && uv run ruff format`
6. Update documentation if API changed
7. Commit and push

## Security Considerations

* **Input Validation**: All inputs validated via Pydantic before CLI execution
* **Command Injection**: sh library handles escaping; no shell=True usage
* **Regex DoS**: Patterns provided by developers, not end users
* **Stderr Leakage**: Error messages may contain sensitive info from stderr

## Monitoring and Logging

```python
# Basic logging implementation
import logging

logger = logging.getLogger('clinch')

# In CLIWrapper._execute():
logger.debug(f"Executing: {self.command} {subcommand} {args}")
logger.debug(f"Exit code: {exit_code}")

# On parsing failure:
logger.warning(f"Failed to parse line {line_num}: {line[:50]}...")

# On error:
logger.error(f"Command failed: {command}, exit code: {exit_code}")
```

Users can configure logging level via standard Python logging:
```python
import logging
logging.getLogger('clinch').setLevel(logging.DEBUG)
```

## Deployment Considerations

Ignored - personal library running on developer's system.

## Migration and Versioning

* **Semantic Versioning**: MAJOR.MINOR.PATCH
* **Breaking Changes**: Allowed - personal library
* **Backward Compatibility**: No guarantees - personal library

---

## Implementation Checklist

* [ ] Core classes implemented with Pydantic
  * [ ] BaseCLIResponse with pattern extraction
  * [ ] BaseCLIError with exception behavior
  * [ ] CLIWrapper with _execute, _build_args, _preprocess_output
* [ ] Custom Field wrapper created
  * [ ] Pattern storage in json_schema_extra
  * [ ] Backward compatible with standard Pydantic Field
* [ ] Parsing engine implemented
  * [ ] Pattern extraction from model fields
  * [ ] Regex application to output
  * [ ] Line-by-line vs full-text parsing logic
  * [ ] Model instantiation from matches
* [ ] ParsingResult and ParsingFailure classes
  * [ ] Success/failure tracking
  * [ ] Metadata capture for failures
  * [ ] Retry mechanism
* [ ] Error handling complete
  * [ ] BaseCLIError raised on non-zero exit
  * [ ] Custom error model parsing
  * [ ] Strict mode implementation
* [ ] sh library integration
  * [ ] Command execution via sh.Command
  * [ ] Stdout/stderr capture
  * [ ] Exit code handling
  * [ ] Timeout support
* [ ] Regex helpers utility module
  * [ ] Common patterns (datetime, email, IP, URL, UUID, semver)
* [ ] Unit tests written and passing
  * [ ] Parsing engine tests
  * [ ] Wrapper tests
  * [ ] Field tests
  * [ ] Error handling tests
* [ ] Integration tests implemented
  * [ ] Real CLI tool tests
  * [ ] Complex parsing scenarios
  * [ ] Timeout and error scenarios
* [ ] Documentation complete
  * [ ] API reference
  * [ ] Usage examples
  * [ ] Migration guide (for future versions)
* [ ] Type checking passes
  * [ ] mypy validation
  * [ ] Full type hint coverage
* [ ] Code quality checks pass
  * [ ] Ruff linting
  * [ ] Ruff formatting
