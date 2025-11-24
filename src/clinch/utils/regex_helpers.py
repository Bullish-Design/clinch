# src/clinch/utils/regex_helpers.py
from __future__ import annotations

"""Common regular expression patterns for CLI parsing."""

ISO_DATETIME: str = (
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?"
)
EMAIL: str = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
IPV4: str = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
IPV6: str = r"(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}"
URL: str = (
    r"https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b"
    r"(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)"
)
UUID: str = (
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
SEMVER: str = r"\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?(?:\+[a-zA-Z0-9.-]+)?"
HEX_COLOR: str = r"#[0-9a-fA-F]{6}"
FILE_PATH: str = r"(?:/[^/\s]+)+/?"
