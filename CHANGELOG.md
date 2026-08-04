# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Pluggable parser architecture: `Parser` protocol with `RegexParser` (the
  default line-by-line engine) and optional `JCParser` adapter for jc's 170+
  battle-tested parsers — `pip install clinch[jc]`
- Pattern-presence semantics for `bool` fields: a bool field's pattern is the
  predicate (matched → `True`), so marker characters like `*` in `git branch`
  work declaratively, with coercible literals (`yes`/`no`/`1`/`0`) honored
- `BaseCLIError.parse_from_stderr` wired into `_execute`, so error subclasses'
  pattern fields are populated from stderr on non-zero exit
- GitHub Actions CI: ruff, mypy strict, pytest with a 90% coverage gate,
  hatch build, twine check — across Python 3.12 / 3.13 / 3.14
- Real-tool jc examples (`ps`, `df`) alongside the existing CSV example

### Changed

- Requires Python ≥ 3.12 (was ≥ 3.13)
- `CLIWrapper._execute` captures stdout through a pipe (`_tty_out=False`),
  fixing TTY-detecting commands that auto-spawn a pager (e.g. `git branch` → `less`)
- Parsing engine modernized to PEP 695 generics (`ParsingResult[T]`,
  `parse_output[TModel]`)
- Examples moved out of the shipped wheel into the root `examples/` directory
- `parse_output` exported from `clinch.parsing`

### Fixed

- sdist referenced a nonexistent `CLInch_SPEC.md`; now ships `DEV_SPEC.md`,
  `docs/`, and `examples/`
- README Quick Start's `git branch` example silently produced zero results
  (bool coercion + TTY pager interaction); verified end-to-end from the wheel
