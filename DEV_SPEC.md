# DEV_SPEC.md

# CLInch Developer Specification

**Version:** 0.1.0  
**Last Updated:** 2024-11-24  
**Status:** Active

## Table of Contents

1. [Introduction](#introduction)
2. [Architecture Overview](#architecture-overview)
3. [Component Responsibilities](#component-responsibilities)
4. [Design Patterns](#design-patterns)
5. [Data Flow](#data-flow)
6. [Development Workflow](#development-workflow)
7. [Testing Strategy](#testing-strategy)
8. [Code Organization](#code-organization)
9. [Extending CLInch](#extending-clinch)
10. [Common Development Tasks](#common-development-tasks)
11. [Quality Standards](#quality-standards)

---

## Introduction

### Purpose

This document orients new developers to the CLInch library architecture, development practices, and patterns. It serves as a comprehensive guide from zero to productive team member.

### Core Philosophy

CLInch follows a **"Pydantic-first"** approach with true object-oriented design:

- **Declarative over Imperative**: Users declare structure, library handles execution
- **Explicit over Implicit**: Patterns must be declared, errors raised by default
- **Type Safety First**: Full type hints, mypy compliance from the start
- **Test-Driven**: Tests written before or alongside implementation
- **Incremental Integration**: No orphaned code—wire up immediately

### Technology Stack

- **Python 3.13+**: Modern Python with full type hint support
- **Pydantic 2.10+**: Data validation and model definition
- **sh 2.0+**: CLI command execution
- **pytest**: Testing framework
- **mypy**: Static type checking
- **ruff**: Linting and formatting
- **uv**: Dependency management

---

## Architecture Overview

### High-Level Structure

```
┌─────────────────────────────────────────────────────────────┐
│                        User Code                            │
│         (Inherits CLIWrapper, defines response models)      │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                     CLIWrapper                              │
│  • Command execution orchestration                          │
│  • Argument building (_build_args)                          │
│  • Output preprocessing (_preprocess_output)                │
│  • Error handling                                           │
│  • Configuration (timeout, strict_mode, error_model)        │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌─────────────┐  ┌──────────────┐  ┌──────────────┐
│  sh Library │  │   Parsing    │  │    Error     │
│  Execution  │  │   Engine     │  │   Handler    │
└─────────────┘  └──────────────┘  └──────────────┘
        │               │               │
        ▼               ▼               ▼
   stdout/stderr    ParsingResult   BaseCLIError
   exit code        (successes +     (typed
                     failures)        exception)
```

### Module Organization

```
src/clinch/
├── __init__.py              # Public API exports
├── fields.py                # Custom Field wrapper
├── exceptions.py            # Exception hierarchy
├── base/
│   ├── response.py          # BaseCLIResponse
│   ├── error.py             # BaseCLIError
│   └── wrapper.py           # CLIWrapper
├── parsing/
│   ├── engine.py            # Parsing implementation
│   └── result.py            # ParsingResult, ParsingFailure
└── utils/
    └── regex_helpers.py     # Common regex patterns
```

### Dependency Graph

```
fields.py
  └→ BaseCLIResponse (uses Field)
      └→ Parsing Engine (extracts patterns)
          └→ ParsingResult (tracks successes/failures)

exceptions.py
  └→ BaseCLIError (uses exceptions)
  └→ CLIWrapper (uses exceptions)

BaseCLIError
  └→ CLIWrapper (error_model)

CLIWrapper
  └→ sh library (command execution)
  └→ BaseCLIResponse (response_model)
  └→ Parsing Engine (via response_model.parse_output)
```

---

## Component Responsibilities

### 1. Custom Field (fields.py)

**Purpose:** Wrap Pydantic's Field to store regex patterns in metadata.

**Responsibilities:**
- Accept `pattern` parameter
- Store pattern in `json_schema_extra`
- Pass through all other Pydantic Field parameters
- Maintain backward compatibility with standard Field

**Key Implementation:**
```python
def Field(
    default: Any = PydanticUndefined,
    *,
    pattern: str | None = None,
    **kwargs: Any
) -> Any:
    json_schema_extra = kwargs.pop('json_schema_extra', {})
    if pattern is not None:
        json_schema_extra['pattern'] = pattern
    
    return PydanticField(default, json_schema_extra=json_schema_extra, **kwargs)
```

**Usage in Models:**
```python
class MyModel(BaseCLIResponse):
    value: str = Field(pattern=r'value: (\w+)')
```

### 2. ParsingResult & ParsingFailure (parsing/result.py)

**Purpose:** Track successful parses and failures separately.

**ParsingResult Responsibilities:**
- Store list of successfully parsed instances
- Store list of parsing failures with metadata
- Provide convenience properties (has_failures, success_count, failure_count)
- Support Generic typing for type safety

**ParsingFailure Responsibilities:**
- Store raw text that failed to parse
- Track attempted patterns
- Capture exception information
- Store line number for debugging
- Provide retry_with_pattern() for alternative parsing

**Key Design Decision:**
Separating successes and failures enables partial failure handling—a core differentiator for CLInch. Users get all successfully parsed data while inspecting failures.

### 3. Exception Hierarchy (exceptions.py)

**Purpose:** Structured error handling throughout the library.

**Hierarchy:**
```
Exception
  └─ CLInchException (base for all CLInch errors)
      ├─ ParsingError (strict mode failures)
      ├─ CommandNotFoundError (CLI tool not found)
      └─ TimeoutError (command timeout exceeded)
```

**Design Principles:**
- All exceptions inherit from CLInchException
- Exceptions carry context (failures, commands, etc.)
- Exception messages are user-friendly
- Never catch and hide exceptions internally

### 4. BaseCLIResponse (base/response.py)

**Purpose:** Base Pydantic model for all CLI output parsing.

**Responsibilities:**
- Extract regex patterns from Field metadata
- Store patterns at class level (`_field_patterns`)
- Coordinate with parsing engine
- Provide `parse_output()` class method

**Pattern Extraction Flow:**
```python
class MyResponse(BaseCLIResponse):
    field: str = Field(pattern=r'value: (\w+)')

# On class definition:
# 1. __init_subclass__ is called
# 2. _extract_field_patterns() runs
# 3. _field_patterns = {'field': r'value: (\w+)'}
# 4. Pattern registry ready for parsing engine
```

**Key Implementation Details:**
- Uses `__init_subclass__` for automatic pattern extraction
- Patterns stored as ClassVar to avoid instance duplication
- Each subclass gets its own `_field_patterns` dict
- Integrates with Pydantic's model validation

### 5. Parsing Engine (parsing/engine.py)

**Purpose:** Apply regex patterns to CLI output and create validated instances.

**Core Functions:**

#### `parse_single_line()`
```python
def parse_single_line(
    line: str,
    model_class: Type[BaseModel],
    patterns: dict[str, str],
    line_number: int = 1
) -> tuple[BaseModel | None, ParsingFailure | None]
```

**Algorithm:**
1. For each field pattern, apply `re.search(pattern, line)`
2. Extract captured group (group 1) if match found
3. Build dict of field_name → value
4. Attempt to create model instance
5. Return (instance, None) on success or (None, failure) on failure

#### `parse_multiline()`
```python
def parse_multiline(
    stdout: str,
    model_class: Type[BaseModel],
    patterns: dict[str, str]
) -> ParsingResult[BaseModel]
```

**Algorithm:**
1. Split stdout into lines
2. For each non-empty line:
   - Call parse_single_line()
   - Add successes to successes list
   - Add failures to failures list
3. Return ParsingResult with both lists

**Design Decisions:**
- All matches extracted (not just first)
- Empty lines skipped silently
- Line numbers tracked (1-indexed)
- Failures captured with full context

### 6. BaseCLIError (base/error.py)

**Purpose:** Structured CLI error information as both Pydantic model and exception.

**Dual Nature:**
```python
class BaseCLIError(BaseModel, Exception):
    exit_code: int
    stderr: str
    stdout: str
    command: str
```

**Responsibilities:**
- Inherit from both BaseModel (for Pydantic validation) and Exception (for raising)
- Store error context (exit code, stderr, stdout, command)
- Support pattern-based parsing of stderr (like BaseCLIResponse)
- Provide readable __str__ representation
- Allow custom error models via subclassing

**Usage in CLIWrapper:**
```python
class CustomError(BaseCLIError):
    error_code: str = Field(pattern=r'ERR-(\d+)')

class MyWrapper(CLIWrapper):
    command = "tool"
    error_model = CustomError
```

### 7. CLIWrapper (base/wrapper.py)

**Purpose:** Orchestrate CLI execution, parsing, and error handling.

**Core Responsibilities:**

#### Command Execution
```python
def _execute(
    self,
    subcommand: str,
    *args: str,
    response_model: Type[T],
    **kwargs: Any
) -> ParsingResult[T] | T
```

**Execution Flow:**
1. Build CLI arguments from kwargs via `_build_args()`
2. Construct full command: `[command, subcommand, *args, *cli_args]`
3. Execute via sh.Command with timeout
4. Check exit code → raise error_model if non-zero
5. Preprocess output via `_preprocess_output()`
6. Parse output via `response_model.parse_output()`
7. Check strict_mode → raise ParsingError if failures
8. Return ParsingResult

#### Argument Building
```python
def _build_args(self, **kwargs: Any) -> list[str]
```

**Default Behavior:**
- `key=value` → `["--key", "value"]`
- `underscore_key=value` → `["--underscore-key", "value"]`
- `flag=True` → `["--flag"]`
- `flag=False` → omitted
- `None` values → omitted
- `list` values → repeated flags

**Customization:**
Override `_build_args()` for tools with non-standard flag formats.

#### Output Preprocessing
```python
def _preprocess_output(self, stdout: str) -> str
```

**Default:** Returns stdout unchanged

**Common Overrides:**
- Strip ANSI color codes
- Normalize whitespace
- Remove headers/footers
- Transform encoding

#### Configuration Attributes
```python
class MyWrapper(CLIWrapper):
    command = "mytool"          # Required
    strict_mode = False         # Raise on parse failures
    timeout = 30                # Command timeout (seconds)
    error_model = CustomError   # Custom error parser
```

---

## Design Patterns

### 1. Template Method Pattern

**Location:** `CLIWrapper._execute()`

**Purpose:** Define execution skeleton, allow customization of steps.

**Fixed Steps:**
- Execute command
- Check exit code
- Parse output
- Return result

**Customizable Hooks:**
- `_build_args()` - Argument formatting
- `_preprocess_output()` - Output transformation
- `error_model` - Error parsing

**Benefits:**
- Consistent execution flow
- Safe customization points
- Testable in isolation

### 2. Strategy Pattern

**Location:** `error_model` attribute

**Purpose:** Allow different error handling strategies.

**Implementation:**
```python
class GitWrapper(CLIWrapper):
    command = "git"
    error_model = GitError  # Custom strategy

class DockerWrapper(CLIWrapper):
    command = "docker"
    error_model = BaseCLIError  # Default strategy
```

**Benefits:**
- Runtime error handler selection
- Custom error parsing per tool
- No conditional logic in CLIWrapper

### 3. Factory Pattern

**Location:** Response model instantiation

**Purpose:** Create validated model instances from parsed data.

**Implementation:**
Pydantic handles factory behavior via model construction:
```python
data = {'field': 'value'}
instance = MyModel(**data)  # Factory method
```

**Benefits:**
- Automatic validation
- Type coercion
- Clear error messages

### 4. Metadata Pattern

**Location:** Field pattern storage

**Purpose:** Store parsing metadata alongside field definitions.

**Implementation:**
```python
class Model(BaseCLIResponse):
    value: str = Field(pattern=r'(\w+)')  # Metadata
    
# Extracted at class definition time:
# Model._field_patterns = {'value': r'(\w+)'}
```

**Benefits:**
- Declarative pattern definition
- Colocation of structure and parsing
- No separate pattern registry

### 5. Result Object Pattern

**Location:** `ParsingResult`

**Purpose:** Return complex operation results with multiple outcomes.

**Implementation:**
```python
@dataclass
class ParsingResult(Generic[T]):
    successes: list[T]
    failures: list[ParsingFailure]
```

**Benefits:**
- Single return type
- Success and failure information
- Type-safe access

---

## Data Flow

### Complete Execution Flow

```
User Code
    │
    ├─→ wrapper.custom_method(**kwargs)
    │       │
    │       └─→ self._execute("subcommand", response_model=Model, **kwargs)
    │
    └─→ CLIWrapper._execute()
            │
            ├─→ _build_args(**kwargs) → ["--flag", "value"]
            │
            ├─→ sh.Command(command)(subcommand, *args, *cli_args)
            │       │
            │       └─→ OS Process → stdout, stderr, exit_code
            │
            ├─→ Exit Code Check
            │       │
            │       └─→ if non-zero: error_model.parse_from_stderr()
            │                            │
            │                            └─→ raise ErrorInstance
            │
            ├─→ _preprocess_output(stdout) → preprocessed_stdout
            │
            ├─→ response_model.parse_output(preprocessed_stdout)
            │       │
            │       └─→ Parsing Engine
            │               │
            │               ├─→ parse_multiline()
            │               │       │
            │               │       ├─→ for each line:
            │               │       │       │
            │               │       │       └─→ parse_single_line()
            │               │       │               │
            │               │       │               ├─→ Apply regex patterns
            │               │       │               │
            │               │       │               ├─→ Extract captures
            │               │       │               │
            │               │       │               ├─→ Build field dict
            │               │       │               │
            │               │       │               └─→ Create model instance
            │               │       │
            │               │       └─→ return ParsingResult(successes, failures)
            │               │
            │               └─→ return result
            │
            ├─→ Strict Mode Check
            │       │
            │       └─→ if strict_mode and result.has_failures:
            │               │
            │               └─→ raise ParsingError(result.failures)
            │
            └─→ return ParsingResult
                    │
                    └─→ User Code accesses:
                            • result.successes
                            • result.failures
                            • result.has_failures
```

### Pattern Extraction Flow

```
Class Definition Time:

class MyResponse(BaseCLIResponse):
    field: str = Field(pattern=r'value: (\w+)')
        │
        └─→ __init_subclass__ triggered
                │
                └─→ _extract_field_patterns()
                        │
                        ├─→ Iterate cls.model_fields
                        │
                        ├─→ Check json_schema_extra['pattern']
                        │
                        └─→ Build pattern dict
                                │
                                └─→ cls._field_patterns = {'field': r'value: (\w+)'}

Runtime:

response_model.parse_output(stdout)
    │
    └─→ Access response_model._field_patterns
            │
            └─→ Pass to parsing engine
```

---

## Development Workflow

### Setup

```bash
# Clone repository
git clone https://github.com/user/clinch.git
cd clinch

# Install dependencies
uv sync

# Verify installation
uv run python -c "import clinch; print(clinch.__version__)"
```

### Branch Strategy

```
main                    # Stable releases
  └─ feature/NAME       # Feature branches
  └─ fix/NAME           # Bug fixes
  └─ docs/NAME          # Documentation updates
```

### Development Cycle

```
1. Create Feature Branch
   git checkout -b feature/my-feature

2. Write Tests First (TDD)
   # Create test file
   touch tests/test_my_feature.py
   
   # Write failing tests
   def test_my_feature():
       assert my_feature() == expected

3. Implement Feature
   # Create source file
   touch src/clinch/my_feature.py
   
   # Implement until tests pass

4. Run Quality Gates
   uv run pytest                    # All tests
   uv run pytest tests/test_my_feature.py  # Specific test
   uv run mypy src/                 # Type checking
   uv run ruff check src/           # Linting
   uv run ruff format src/          # Formatting

5. Verify Coverage
   uv run pytest --cov=src/clinch --cov-report=term-missing
   # Ensure ≥90% coverage

6. Commit and Push
   git add .
   git commit -m "feat: add my feature"
   git push origin feature/my-feature

7. Create Pull Request
   # Ensure all CI checks pass
```

### Quality Gates Checklist

Before committing, verify:
- [ ] All tests pass (`pytest`)
- [ ] Type checking clean (`mypy src/`)
- [ ] Linting clean (`ruff check src/`)
- [ ] Formatting applied (`ruff format src/`)
- [ ] Coverage ≥90%
- [ ] No TODOs or FIXMEs
- [ ] Docstrings added for public APIs
- [ ] Examples in docstrings work

---

## Testing Strategy

### Test Organization

```
tests/
├── test_fields.py              # Unit: Custom Field
├── test_parsing_result.py      # Unit: ParsingResult/Failure
├── test_exceptions.py          # Unit: Exception hierarchy
├── test_regex_helpers.py       # Unit: Regex patterns
├── test_base_response.py       # Unit: BaseCLIResponse
├── test_base_error.py          # Unit: BaseCLIError
├── test_parsing_engine.py      # Unit: Parsing logic
├── test_wrapper.py             # Unit + Integration: CLIWrapper
└── integration/
    ├── test_real_tools.py      # Integration: Real CLI tools
    └── test_examples.py        # Integration: Example wrappers
```

### Test Levels

#### 1. Unit Tests

**Focus:** Individual functions/methods in isolation

**Example:**
```python
def test_field_stores_pattern():
    class Model(BaseModel):
        value: str = Field(pattern=r'test: (\w+)')
    
    field_info = Model.model_fields['value']
    assert field_info.json_schema_extra['pattern'] == r'test: (\w+)'
```

**Characteristics:**
- Fast execution (<1ms per test)
- No external dependencies
- Mock CLI execution if needed
- Test edge cases exhaustively

#### 2. Integration Tests

**Focus:** Components working together

**Example:**
```python
def test_full_parsing_flow():
    class Response(BaseCLIResponse):
        value: str = Field(pattern=r'value: (\w+)')
    
    class Wrapper(CLIWrapper):
        command = "echo"
    
    wrapper = Wrapper()
    result = wrapper._execute("value: hello", response_model=Response)
    
    assert result.success_count == 1
    assert result.successes[0].value == "hello"
```

**Characteristics:**
- Use real CLI commands (echo, ls, etc.)
- Test full execution flow
- Verify error handling
- Test configuration combinations

#### 3. Example Tests

**Focus:** Real-world usage patterns

**Example:**
```python
def test_git_wrapper():
    git = GitWrapper()
    result = git.branches()
    
    assert result.success_count > 0
    assert all(isinstance(b, GitBranch) for b in result.successes)
```

**Characteristics:**
- Verify examples in documentation work
- Catch breaking changes
- Serve as usage documentation

### Test Patterns

#### Arrange-Act-Assert

```python
def test_feature():
    # Arrange
    model = MyModel()
    expected = "value"
    
    # Act
    result = model.method()
    
    # Assert
    assert result == expected
```

#### Parameterized Tests

```python
@pytest.mark.parametrize("input,expected", [
    ("value: hello", "hello"),
    ("value: world", "world"),
])
def test_parsing(input, expected):
    result = parse(input)
    assert result.value == expected
```

#### Fixture Usage

```python
@pytest.fixture
def wrapper():
    return MyWrapper()

def test_with_fixture(wrapper):
    result = wrapper.method()
    assert result.success_count > 0
```

### Coverage Requirements

- **Overall:** ≥90%
- **Critical Paths:** 100% (parsing, error handling, execution)
- **Edge Cases:** All branches covered
- **Error Paths:** All exceptions tested

**Check Coverage:**
```bash
uv run pytest --cov=src/clinch --cov-report=html
# Open htmlcov/index.html
```

---

## Code Organization

### File Structure Principles

1. **One responsibility per file**
   - `fields.py` - Only Field implementation
   - `exceptions.py` - Only exception classes
   - Each module has clear purpose

2. **Related code stays together**
   - `base/` - Core abstractions
   - `parsing/` - Parsing functionality
   - `utils/` - Utilities and helpers

3. **Public API in __init__.py**
   - Explicit exports
   - Clear public interface
   - Hide implementation details

### Imports

**Every file starts with:**
```python
# src/clinch/my_module.py
from __future__ import annotations
```

**Import order:**
```python
# 1. Future imports
from __future__ import annotations

# 2. Standard library
import re
from typing import Any, TypeVar

# 3. Third-party
from pydantic import BaseModel, Field

# 4. Local imports
from clinch.exceptions import ParsingError
from clinch.parsing.result import ParsingResult
```

### Naming Conventions

- **Classes:** PascalCase (`BaseCLIResponse`, `ParsingResult`)
- **Functions/Methods:** snake_case (`_build_args`, `parse_output`)
- **Constants:** UPPER_SNAKE_CASE (`ISO_DATETIME`)
- **Private:** Leading underscore (`_field_patterns`, `_execute`)
- **Protected:** No convention (use docstrings to indicate intended use)

### Documentation

**Docstring Format:**
```python
def function(param: str) -> int:
    """Short one-line summary.
    
    Longer description explaining purpose, behavior, and any
    important details.
    
    Args:
        param: Description of parameter
        
    Returns:
        Description of return value
        
    Raises:
        ErrorType: When this error occurs
        
    Examples:
        >>> function("test")
        42
    """
```

**When to Document:**
- All public classes
- All public methods/functions
- Complex private methods
- Non-obvious implementation details

### Type Hints

**Always use type hints:**
```python
def parse_line(line: str, model: Type[BaseModel]) -> BaseModel | None:
    ...
```

**Generic types:**
```python
from typing import TypeVar, Generic

T = TypeVar('T', bound=BaseModel)

class Container(Generic[T]):
    items: list[T]
```

**Use `from __future__ import annotations` to avoid quotes:**
```python
# Good
def method(self) -> BaseCLIResponse:
    ...

# Avoid (no annotations import)
def method(self) -> "BaseCLIResponse":
    ...
```

---

## Extending CLInch

### Adding New Response Types

**Example: Single-line response**
```python
# src/clinch/base/response.py

class BaseCLISingleResponse(BaseCLIResponse):
    """Response model that expects single-line output."""
    
    @classmethod
    def parse_output(cls, stdout: str) -> Self:
        """Parse single line into model instance.
        
        Raises ParsingError if output is multiple lines or fails to parse.
        """
        lines = [line for line in stdout.splitlines() if line.strip()]
        
        if len(lines) != 1:
            raise ParsingError(f"Expected single line, got {len(lines)}")
        
        result = super().parse_output(stdout)
        if result.failure_count > 0:
            raise ParsingError(result.failures)
        
        return result.successes[0]
```

**Usage:**
```python
class DockerVersion(BaseCLISingleResponse):
    version: str = Field(pattern=r'Docker version (\S+)')

version = docker.version()  # Returns DockerVersion, not ParsingResult
```

### Adding New Regex Patterns

**Location:** `src/clinch/utils/regex_helpers.py`

```python
# Add to regex_helpers.py

# Pattern for MAC addresses
MAC_ADDRESS = r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})'
"""
Matches MAC addresses in formats:
- AA:BB:CC:DD:EE:FF
- AA-BB-CC-DD-EE-FF

Examples:
    >>> re.search(MAC_ADDRESS, "Device MAC: AA:BB:CC:DD:EE:FF")
    <Match object>
"""
```

**Testing:**
```python
# tests/test_regex_helpers.py

def test_mac_address_pattern():
    from clinch.utils import regex_helpers
    import re
    
    valid = [
        "AA:BB:CC:DD:EE:FF",
        "00-11-22-33-44-55",
        "Device MAC: AA:BB:CC:DD:EE:FF"
    ]
    
    for text in valid:
        assert re.search(regex_helpers.MAC_ADDRESS, text)
```

### Adding New Wrapper Features

**Example: Dry-run mode**

```python
# src/clinch/base/wrapper.py

class CLIWrapper:
    command: str
    strict_mode: bool = False
    timeout: int | None = None
    error_model: Type[BaseCLIError] = BaseCLIError
    dry_run: bool = False  # New feature
    
    def _execute(
        self,
        subcommand: str,
        *args: str,
        response_model: Type[T],
        **kwargs: Any
    ) -> ParsingResult[T] | T:
        cli_args = self._build_args(**kwargs)
        full_command = [self.command, subcommand, *args, *cli_args]
        
        # New feature: dry-run mode
        if self.dry_run:
            print(f"Would execute: {' '.join(full_command)}")
            return ParsingResult()  # Empty result
        
        # ... rest of execution
```

**Testing:**
```python
def test_dry_run_mode(capsys):
    class TestWrapper(CLIWrapper):
        command = "echo"
        dry_run = True
    
    wrapper = TestWrapper()
    wrapper._execute("hello", response_model=MyModel)
    
    captured = capsys.readouterr()
    assert "Would execute: echo hello" in captured.out
```

### Creating Tool-Specific Wrappers

**Best Practices:**

1. **Create separate package:** `clinch-tools`
2. **One wrapper per file:** `clinch_tools/git.py`
3. **Full type hints**
4. **Comprehensive tests**
5. **Documentation with examples**

**Example Structure:**
```python
# clinch_tools/git.py

from clinch import CLIWrapper, BaseCLIResponse, Field

class GitCommit(BaseCLIResponse):
    """Single git commit."""
    hash: str = Field(pattern=r'^([a-f0-9]{7,40})')
    author: str = Field(pattern=r'Author: (.+) <')
    date: str = Field(pattern=r'Date:\s+(.+)')
    message: str = Field(pattern=r'\n\s{4}(.+)')

class GitWrapper(CLIWrapper):
    """Type-safe interface to git CLI."""
    command = "git"
    
    def log(self, max_count: int = 10, branch: str | None = None) -> list[GitCommit]:
        """Get commit log.
        
        Args:
            max_count: Maximum number of commits
            branch: Branch to query (default: current)
            
        Returns:
            List of parsed commits
            
        Example:
            >>> git = GitWrapper()
            >>> commits = git.log(max_count=5)
            >>> for commit in commits.successes:
            ...     print(commit.hash, commit.message)
        """
        args = ["log", "--format=fuller"]
        if branch:
            args.append(branch)
            
        return self._execute(
            *args,
            max_count=max_count,
            response_model=GitCommit
        )
```

---

## Common Development Tasks

### Adding a New Field Type

**Scenario:** Add support for duration parsing (e.g., "5m30s")

**Steps:**

1. **Add pattern to regex_helpers**
```python
# src/clinch/utils/regex_helpers.py

DURATION = r'(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?'
"""Matches duration strings like 5m30s, 2h15m, 90s"""
```

2. **Create custom field validator if needed**
```python
# User code (or add to clinch if generally useful)

from pydantic import field_validator

class MyModel(BaseCLIResponse):
    duration: str = Field(pattern=regex_helpers.DURATION)
    
    @field_validator('duration')
    @classmethod
    def parse_duration(cls, v: str) -> int:
        """Convert duration string to seconds."""
        # Parse and return seconds
        ...
```

3. **Add tests**
```python
def test_duration_pattern():
    assert re.match(regex_helpers.DURATION, "5m30s")
    assert re.match(regex_helpers.DURATION, "2h15m")
```

### Debugging Parse Failures

**Scenario:** Output not parsing correctly

**Approach:**

1. **Check actual output**
```python
# Add print statement before parsing
def _execute(self, ...):
    # ...
    print(f"Raw output:\n{stdout}")  # Debug line
    result = response_model.parse_output(stdout)
```

2. **Test patterns in isolation**
```python
import re

output_line = "value: hello world"
pattern = r'value: (\w+)'

match = re.search(pattern, output_line)
if match:
    print(match.group(1))  # "hello" - only first word!
else:
    print("No match")

# Fix: r'value: (.+)' to match all
```

3. **Check ParsingFailure details**
```python
result = wrapper.parse()

for failure in result.failures:
    print(f"Line {failure.line_number}: {failure.raw_text}")
    print(f"Tried patterns: {failure.attempted_patterns}")
    print(f"Exception: {failure.exception}")
```

4. **Use verbose regex matching**
```python
import re

pattern = r'(?P<field>\w+): (?P<value>.+)'
match = re.search(pattern, line)
if match:
    print(match.groupdict())  # {'field': 'name', 'value': 'test'}
```

### Adding Tests for Real CLI Tools

**Scenario:** Test wrapper with actual git/docker/etc.

**Approach:**

1. **Check if tool available**
```python
import pytest
import shutil

@pytest.mark.skipif(
    shutil.which("git") is None,
    reason="git not available"
)
def test_git_wrapper():
    git = GitWrapper()
    result = git.status()
    assert result.success_count >= 0
```

2. **Use temporary git repo for testing**
```python
import tempfile
import os

@pytest.fixture
def git_repo(tmp_path):
    """Create temporary git repository."""
    os.chdir(tmp_path)
    os.system("git init")
    os.system("git config user.email 'test@test.com'")
    os.system("git config user.name 'Test User'")
    (tmp_path / "file.txt").write_text("test")
    os.system("git add file.txt")
    os.system("git commit -m 'test'")
    return tmp_path

def test_git_log(git_repo):
    git = GitWrapper()
    result = git.log(max_count=1)
    assert result.success_count == 1
```

3. **Mock for unit tests**
```python
from unittest.mock import patch, MagicMock

def test_git_wrapper_unit():
    with patch('sh.Command') as mock_cmd:
        mock_git = MagicMock()
        mock_git.return_value = MagicMock(stdout="* main\n  develop")
        mock_cmd.return_value = mock_git
        
        git = GitWrapper()
        result = git.branches()
        
        assert result.success_count == 2
```

### Performance Optimization

**Profiling:**
```bash
# Profile parsing performance
python -m cProfile -s cumtime -m pytest tests/test_parsing_engine.py

# Use pytest-benchmark for timing
uv add --dev pytest-benchmark

# In test file
def test_parsing_speed(benchmark):
    result = benchmark(parse_multiline, large_output, Model, patterns)
    assert result.success_count > 0
```

**Optimization Techniques:**

1. **Compile regex patterns once**
```python
# Bad: Recompiles every time
def parse(line):
    match = re.search(r'pattern: (\w+)', line)

# Good: Compile once
PATTERN = re.compile(r'pattern: (\w+)')
def parse(line):
    match = PATTERN.search(line)
```

2. **Cache pattern extraction**
```python
# Already done in BaseCLIResponse via _field_patterns ClassVar
```

3. **Batch processing**
```python
# Process lines in batches for large outputs
def parse_batched(lines, batch_size=1000):
    for i in range(0, len(lines), batch_size):
        batch = lines[i:i+batch_size]
        yield from process_batch(batch)
```

---

## Quality Standards

### Code Quality Metrics

**Enforced by CI:**
- pytest: All tests must pass
- mypy: No type errors
- ruff check: No linting errors
- ruff format: Code properly formatted
- pytest --cov: ≥90% coverage

### Code Review Checklist

**For Reviewers:**
- [ ] Tests added for new functionality
- [ ] Tests cover edge cases
- [ ] Type hints present and correct
- [ ] Docstrings added for public APIs
- [ ] No breaking changes (or documented)
- [ ] Performance impact assessed
- [ ] Error messages are clear
- [ ] Code follows existing patterns
- [ ] No unnecessary complexity

**For Authors:**
- [ ] Self-review completed
- [ ] All quality gates pass locally
- [ ] Examples in docstrings work
- [ ] Documentation updated if needed
- [ ] CHANGELOG.md updated (for releases)
- [ ] Breaking changes noted

### Performance Standards

**Target Metrics:**
- Parsing overhead: <5ms per command
- Pattern compilation: Cached at class level
- Memory usage: O(n) where n = output lines
- Test suite: <10s for full run

### Error Message Standards

**Good Error Messages:**
```python
# Bad
raise ValueError("Invalid input")

# Good
raise ValueError(
    f"Pattern '{pattern}' failed to match line {line_num}: '{line[:50]}...'"
)
```

**Principles:**
- Include relevant context
- Show what was expected
- Show what was received
- Suggest fix if possible
- Reference line numbers

### Documentation Standards

**Every public API must have:**
- One-line summary
- Detailed description
- Args documentation
- Returns documentation
- Raises documentation (if applicable)
- At least one usage example

**Example:**
```python
def parse_output(cls, stdout: str) -> ParsingResult[Self]:
    """Parse CLI output into model instances.
    
    Applies regex patterns from Field metadata to each line of output,
    creating validated model instances for successful matches and
    tracking failures for debugging.
    
    Args:
        stdout: Raw CLI output to parse
        
    Returns:
        ParsingResult containing successfully parsed instances and
        any parsing failures with metadata
        
    Raises:
        ParsingError: If strict_mode=True and any line fails to parse
        
    Examples:
        >>> class MyModel(BaseCLIResponse):
        ...     value: str = Field(pattern=r'value: (\w+)')
        >>> result = MyModel.parse_output("value: hello\\nvalue: world")
        >>> len(result.successes)
        2
    """
```

---

## Appendix

### Useful Commands

```bash
# Run specific test
uv run pytest tests/test_wrapper.py::test_execute_success -v

# Run with coverage
uv run pytest --cov=src/clinch --cov-report=html

# Type check single file
uv run mypy src/clinch/base/wrapper.py

# Format specific file
uv run ruff format src/clinch/base/wrapper.py

# Check for type issues
uv run mypy src/ --show-error-codes

# Run tests matching pattern
uv run pytest -k "parse" -v

# Debug test
uv run pytest tests/test_wrapper.py -v -s --pdb
```

### Common Issues

**Issue:** Pattern doesn't match output  
**Solution:** Test regex in isolation, check for special characters, verify capture groups

**Issue:** Pydantic validation fails  
**Solution:** Check field types match regex output, add validators if needed

**Issue:** sh library errors  
**Solution:** Verify command exists in PATH, check timeout setting

**Issue:** Type errors with Generic[T]  
**Solution:** Ensure T is bound correctly, check TypeVar definition

### Resources

- **Pydantic Docs:** https://docs.pydantic.dev/
- **Python Regex:** https://docs.python.org/3/library/re.html
- **sh Library:** https://sh.readthedocs.io/
- **pytest Docs:** https://docs.pytest.org/

### Contact

For questions or contributions, see CONTRIBUTING.md or open an issue on GitHub.

---

**End of Developer Specification**
