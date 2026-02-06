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
        "CommandTimeoutError",
        "TimeoutError",
        "regex_helpers",
        "BaseCLIResponse",
        "BaseCLIError",
        "CLIWrapper",
        "BaseCLICommand",
    ]:
        assert name in public, f"{name} not in __all__"
