# tests/test_smoke.py
from __future__ import annotations

import clinch
import clinch.base  # noqa: F401
import clinch.parsing  # noqa: F401
import clinch.utils  # noqa: F401
from clinch import (
    BaseCLIError,
    BaseCLIResponse,
    CLInchException,
    CommandNotFoundError,
    Field,
    ParsingError,
    ParsingFailure,
    ParsingResult,
    TimeoutError,
    regex_helpers,
)


def test_import_clinch_package_and_exports() -> None:
    assert clinch is not None
    assert Field is not None
    assert ParsingResult is not None
    assert ParsingFailure is not None
    assert CLInchException is not None
    assert ParsingError is not None
    assert CommandNotFoundError is not None
    assert TimeoutError is not None
    assert regex_helpers is not None
    assert BaseCLIResponse is not None
    assert BaseCLIError is not None
