# tests/test_public_api.py
from __future__ import annotations

import clinch


def test_public_api_exports() -> None:
    public = set(clinch.__all__)
    for name in [
        "Field",
        "ParsingFailure",
        "ParsingResult",
        "CLInchException",
        "ParsingError",
        "CommandNotFoundError",
        "TimeoutError",
        "regex_helpers",
        "BaseCLIResponse",
        "BaseCLIError",
        "CLIWrapper",
    ]:
        assert name in public
