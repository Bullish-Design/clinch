# tests/test_smoke.py
from __future__ import annotations

import clinch
import clinch.base  # noqa: F401
import clinch.parsing  # noqa: F401
import clinch.utils  # noqa: F401


def test_import_clinch_package() -> None:
    assert clinch is not None
