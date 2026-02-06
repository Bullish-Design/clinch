# CLInch Developer Guide

This document is for maintainers and contributors. It covers architecture, codebase layout, design decisions, and how to work on the project.

## Project Layout

```
src/clinch/
    __init__.py              # Public API — all user-facing exports
    fields.py                # Field() wrapper — stores regex pattern in Pydantic metadata
    exceptions.py            # Exception hierarchy
    base/
        __init__.py          # Re-exports BaseCLIResponse, CLIWrapper, BaseCLIError, BaseCLICommand
        response.py          # BaseCLIResponse + _PatternMixin
        wrapper.py           # CLIWrapper (sync + async execution)
        error.py             # BaseCLIError (exception with pattern-based stderr parsing)
        command.py           # BaseCLICommand (command-as-object pattern)
    parsing/
        __init__.py          # Re-exports ParsingResult, ParsingFailure
        result.py            # ParsingResult[T] and ParsingFailure
        engine.py            # parse_output(), parse_blocks(), pattern cache
    utils/
        regex_helpers.py     # Pre-built regex patterns (ISO_DATETIME, EMAIL, IPV4, etc.)
    examples/
        echo.py              # EchoWrapper — minimal working example
        ls.py                # LsWrapper — directory listing example
tests/
    test_public_api.py       # Verifies __all__ exports match expectations
    test_smoke.py            # Import smoke tests and version check
    test_exceptions.py       # Exception hierarchy and messages
    test_fields.py           # Field pattern metadata storage
    test_parsing_result.py   # ParsingResult API (iter, len, slice, filter, map)
    test_parsing_engine.py   # parse_output, parse_blocks, named groups, caching
    test_regex_helpers.py    # All regex helper patterns
    test_base_response.py    # BaseCLIResponse pattern extraction and inheritance
    test_base_error.py       # BaseCLIError creation and stderr parsing
    test_command.py          # BaseCLICommand auto build_args
    test_wrapper.py          # CLIWrapper execution, arg building, error handling
    test_async.py            # Async execution tests
    test_wrapper_validation.py  # Pydantic validation on wrappers
    test_advanced_responses.py  # Computed fields, validators, serializers
    integration/
        test_examples.py     # Built-in echo/ls examples
        test_examples_usage.py  # Example module imports
        test_real_tools.py   # Real CLI tools (echo, ls)
```

## Architecture

The library has four layers. Data flows top-to-bottom during execution:

```
CLIWrapper / BaseCLICommand       ← Execution layer (runs CLI, handles errors)
        │
        ▼
BaseCLIResponse                   ← Model layer (defines output structure)
        │
        ▼
parsing engine                    ← Parsing layer (regex matching, value extraction)
        │
        ▼
ParsingResult[T]                  ← Result layer (successes + failures)
```

### Layer 1: Execution (`base/wrapper.py`)

`CLIWrapper` is responsible for:
- Running the CLI command via `sh` (sync) or `asyncio.create_subprocess_exec` (async)
- Converting Python kwargs to CLI flags (`_build_args`)
- Catching `sh` exceptions and converting them to CLInch exceptions
- Passing stdout to the response model's `parse_output()`
- Enforcing strict mode (raise on any parse failure)

The wrapper never parses output directly. It delegates to the response model, which delegates to the parsing engine.

### Layer 2: Models (`base/response.py`, `base/error.py`, `base/command.py`)

**`BaseCLIResponse`** is a Pydantic `BaseModel` subclass. Its job:
- Collect `pattern` metadata from fields via `__pydantic_init_subclass__`
- Walk the MRO to merge inherited patterns (`_merge_parent_patterns`)
- Expose `parse_output()` and `parse_blocks()` as class methods that delegate to the engine

**`BaseCLIError`** is an `Exception` subclass (not a BaseModel) that also uses `_PatternMixin`. It can optionally parse structured data from stderr using the same pattern system. It dynamically creates a temporary Pydantic model via `pydantic.create_model` for parsing, then attaches extracted values as instance attributes.

**`BaseCLICommand`** is a Pydantic `BaseModel` that represents a command invocation as an object. It auto-converts its fields to CLI flags in `build_args()` and carries a `response_model` class variable so the wrapper knows how to parse the result.

### Layer 3: Parsing (`parsing/engine.py`)

Two parsing functions:

- **`parse_output(model, output)`** — Line-by-line parsing. Each non-blank line is matched against all field patterns. Extracted values are passed to the model constructor.
- **`parse_blocks(model, output, delimiter)`** — Block-based parsing. Lines are grouped by a delimiter (blank line by default). All lines in a block are matched, and extracted values are merged into a single model instance. Use this for multi-line records like `git log` or `apt show` output.

Both return `ParsingResult[T]`.

Pattern matching supports three modes (implemented in `_extract_match_values`):
1. Named groups (`(?P<name>...)`) — maps directly to field names, can populate multiple fields from one pattern
2. Single capture group (`(...)`) — maps to the field the pattern belongs to
3. No capture group — full match (`group(0)`) maps to the field

Compiled patterns are cached with `functools.lru_cache(maxsize=256)`.

### Layer 4: Results (`parsing/result.py`)

`ParsingResult[T]` holds two lists: `successes` and `failures`. It implements `__iter__`, `__len__`, and `__getitem__` over successes, so you can treat it like a list in simple cases. It also provides `filter_successes()`, `map_successes()`, `raise_if_failures()`, and `get_failure_summary()`.

`ParsingFailure` records what went wrong: the raw text, line number, which patterns were attempted, and any Pydantic validation exception.

## Key Design Decisions

### Patterns in Pydantic metadata

Regex patterns are stored in `json_schema_extra["pattern"]` on each field. This keeps the pattern co-located with the field definition and avoids a separate mapping. The `Field()` wrapper in `fields.py` handles this transparently.

### Partial failure by default

The parsing engine never raises on a failed line. It records the failure and moves on. This is deliberate — CLI output often has headers, footers, or irregular lines mixed with the data you want. Strict mode is opt-in via `CLIWrapper.strict_mode = True`.

### _PatternMixin for shared logic

Both `BaseCLIResponse` and `BaseCLIError` need pattern extraction. The shared logic lives in `_PatternMixin`, which provides `_field_patterns` and `_merge_parent_patterns()`. The two classes implement `_extract_field_patterns()` differently because `BaseCLIResponse` reads from Pydantic's `model_fields` while `BaseCLIError` scans class `__dict__` for `FieldInfo` descriptors (since it's not a BaseModel).

### Error model as exception

`BaseCLIError` inherits from `Exception`, not `BaseModel`. This lets it be raised and caught naturally. Pattern-based stderr parsing is done via a temporary `create_model()` call in `parse_from_stderr()`, not by making the error itself a model.

### Wrapper uses `sh` for sync, `asyncio` for async

Sync execution uses the `sh` library for its clean API and timeout handling. Async execution uses `asyncio.create_subprocess_exec` directly — `sh` doesn't have native async support.

## Working on the Project

### Setup

```bash
git clone <repo-url>
cd clinch
uv sync --dev
```

### Running Tests

```bash
uv run pytest                        # All tests with coverage
uv run pytest tests/test_wrapper.py  # Single file
uv run pytest -k "test_async"        # By name pattern
uv run pytest -x                     # Stop on first failure
```

Tests use `pytest-asyncio` (with `asyncio_mode = "auto"`) and `pytest-cov`. Coverage is configured in `pyproject.toml` to report on `src/clinch`.

### Linting and Type Checking

```bash
uv run ruff check src/ tests/        # Lint
uv run ruff format src/ tests/       # Format
uv run mypy src/                     # Type check (strict mode)
```

Ruff is configured for line length 120, targeting Python 3.13. Selected rule sets: F, E, W, I, N, UP, B, A. E501 (line length) is ignored since we set line-length=120.

mypy runs in strict mode with `disallow_untyped_defs = true`.

### Adding a New Feature

Typical flow for adding new functionality:

1. **Response model** — If the feature involves parsing new CLI output, add a `BaseCLIResponse` subclass. Define fields with `Field(pattern=...)`.
2. **Wrapper method** — Add a method on the relevant `CLIWrapper` subclass that calls `_execute()` or `_execute_async()` with the response model.
3. **Command object** (optional) — If the command has reusable parameters, create a `BaseCLICommand` subclass.
4. **Tests** — Add unit tests for the response model (parse known output strings). Add wrapper tests using monkeypatch to mock `sh.Command`.
5. **Integration tests** — If the feature works with a universally-available tool (echo, ls, etc.), add an integration test under `tests/integration/`.

### Testing Patterns

**Parsing tests** — Test response models directly without running any CLI commands:

```python
def test_my_response():
    output = "name: foo\nname: bar"
    result = MyResponse.parse_output(output)
    assert result.success_count == 2
    assert result[0].name == "foo"
```

**Wrapper tests** — Mock `sh.Command` via monkeypatch to avoid needing the real CLI tool:

```python
def test_wrapper(monkeypatch):
    def fake_cmd(*args, **kwargs):
        class FakeResult:
            stdout = "mocked output"
        return FakeResult()

    monkeypatch.setattr("sh.Command", lambda name: fake_cmd)
    wrapper = MyWrapper()
    result = wrapper.my_method()
    assert result.success_count == 1
```

**Async tests** — Use `@pytest.mark.asyncio` (auto mode is enabled, so just defining `async def test_...` works):

```python
async def test_async_execution():
    wrapper = MyWrapper()
    result = await wrapper.my_async_method()
    assert result.success_count > 0
```

### Common Pitfalls

- **Forgetting `pattern=` in Field** — Without a pattern, the parsing engine has nothing to match. The field won't be populated and you'll get validation errors or empty results.
- **Capture groups vs. named groups** — Don't mix them in one pattern. If named groups are present, unnamed capture groups are ignored.
- **Pattern matches multiple fields** — The engine tries all patterns against each line. If two patterns match the same text, both fields get populated. This is by design but can cause surprises.
- **BaseCLIError field cleanup** — `__init_subclass__` on `BaseCLIError` deletes `FieldInfo` descriptors from the class after extracting patterns. This means you can't introspect those fields on the class after definition.
- **`command` is a ClassVar** — Setting `command` as an instance attribute won't work. It must be defined on the class body.

## Dependencies

| Package | Role |
|---|---|
| `pydantic >= 2.10` | Model validation, field metadata, BaseModel |
| `sh >= 2.0` | Sync subprocess execution |
| `pytest >= 8.0` | Test framework (dev) |
| `pytest-cov >= 4.0` | Coverage reporting (dev) |
| `pytest-asyncio >= 0.23` | Async test support (dev) |
| `ruff >= 0.1` | Linting and formatting (dev) |
| `mypy >= 1.8` | Static type checking (dev) |
