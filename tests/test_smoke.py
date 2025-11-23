# tests/test_smoke.py
from __future__ import annotations

import clinch
import clinch.base  # noqa: F401
import clinch.parsing  # noqa: F401
import clinch.utils  # noqa: F401

from clinch import Field, ParsingFailure, ParsingResult


def test_import_clinch_package_and_exports() -> None:
    assert clinch is not None
    assert Field is not None
    assert ParsingResult is not None
    assert ParsingFailure is not None
