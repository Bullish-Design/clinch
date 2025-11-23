# src/clinch/utils/regex_helpers.py
from __future__ import annotations

"""Common regular expression patterns for CLI parsing.

These patterns cover frequently encountered data types in CLI output,
such as timestamps, network addresses, and identifiers. They are
intended to be used with :func:`clinch.Field` so that models can
declare patterns in a reusable, consistent way.
"""

# ISO 8601 datetime (e.g., "2024-11-22T10:30:00Z", with optional fractional
# seconds and timezone offsets like "+05:30").
ISO_DATETIME: str = (
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?"
)

# Email addresses like "user@example.com". This is a pragmatic pattern, not a
# full RFC-complete implementation.
EMAIL: str = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

# IPv4 addresses in dotted-quad form, e.g., "192.168.0.1". This pattern does
# not enforce octet range validity (0-255), only general structure.
IPV4: str = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"

# Simplified IPv6 addresses in full notation, e.g.,
# "2001:0db8:85a3:0000:0000:8a2e:0370:7334". Compressed forms are not
# supported.
IPV6: str = r"(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}"

# HTTP/HTTPS URLs such as "https://example.com/path?query=1". This pattern is
# intentionally broad and not a fully strict URL validator.
URL: str = (
    r"https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b"
    r"(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)"
)

# UUID values like "123e4567-e89b-12d3-a456-426614174000".
UUID: str = (
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)

# Semantic version strings such as "1.2.3", "1.2.3-alpha", or
# "1.2.3-alpha+build.1".
SEMVER: str = r"\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?(?:\+[a-zA-Z0-9.-]+)?"

# Hex color codes in the form "#1a2b3c".
HEX_COLOR: str = r"#[0-9a-fA-F]{6}"

# Unix-style absolute file paths like "/usr/local/bin/python".
FILE_PATH: str = r"(?:/[^/\s]+)+/?"
