# tests/test_regex_helpers.py
from __future__ import annotations

import re

from pydantic import BaseModel

from clinch.fields import Field
from clinch.utils import regex_helpers


class EmailModel(BaseModel):
    email: str = Field(pattern=regex_helpers.EMAIL)


def test_iso_datetime_valid() -> None:
    pattern = regex_helpers.ISO_DATETIME
    valid_dates = [
        "2024-11-22T10:30:00Z",
        "2024-01-01T00:00:00.123Z",
        "2024-11-22T10:30:00+05:30",
    ]
    for date in valid_dates:
        match = re.fullmatch(pattern, date)
        assert match is not None, f"Failed to match: {date}"


def test_iso_datetime_invalid() -> None:
    pattern = regex_helpers.ISO_DATETIME
    invalid_dates = [
        "2024-11-22",
        "10:30:00Z",
        "not-a-date",
    ]
    for date in invalid_dates:
        match = re.fullmatch(pattern, date)
        assert match is None, f"Unexpectedly matched: {date}"


def test_email_pattern_positive_and_negative() -> None:
    pattern = regex_helpers.EMAIL
    assert re.fullmatch(pattern, "user@example.com")
    assert re.fullmatch(pattern, "user.name+tag@example.co.uk")
    assert not re.fullmatch(pattern, "user@")
    assert not re.fullmatch(pattern, "not-an-email")


def test_ipv4_pattern_positive_and_negative() -> None:
    pattern = regex_helpers.IPV4
    assert re.search(pattern, "ip=192.168.0.1")
    assert not re.search(pattern, "192.168.0")


def test_ipv6_pattern_positive_and_negative() -> None:
    pattern = regex_helpers.IPV6
    assert re.fullmatch(pattern, "2001:0db8:85a3:0000:0000:8a2e:0370:7334")
    assert not re.fullmatch(pattern, "not-an-ipv6")


def test_url_pattern_positive_and_negative() -> None:
    pattern = regex_helpers.URL
    assert re.search(pattern, "Visit https://example.com/path?x=1 for more")
    assert not re.search(pattern, "ftp://example.com")


def test_uuid_pattern_positive_and_negative() -> None:
    pattern = regex_helpers.UUID
    assert re.fullmatch(pattern, "123e4567-e89b-12d3-a456-426614174000")
    assert not re.fullmatch(pattern, "not-a-uuid")


def test_semver_pattern_positive_and_negative() -> None:
    pattern = regex_helpers.SEMVER
    assert re.fullmatch(pattern, "1.2.3")
    assert re.fullmatch(pattern, "1.2.3-alpha+build.1")
    assert not re.fullmatch(pattern, "1.2")
    assert not re.fullmatch(pattern, "1.2.3.4")


def test_hex_color_pattern_positive_and_negative() -> None:
    pattern = regex_helpers.HEX_COLOR
    assert re.fullmatch(pattern, "#1a2b3c")
    assert not re.fullmatch(pattern, "1a2b3c")
    assert not re.fullmatch(pattern, "#xyzxyz")


def test_file_path_pattern_positive_and_negative() -> None:
    pattern = regex_helpers.FILE_PATH
    assert re.fullmatch(pattern, "/usr/local/bin/python")
    assert not re.fullmatch(pattern, "relative/path")


def test_email_field_uses_email_pattern() -> None:
    field_info = EmailModel.model_fields["email"]
    assert field_info.json_schema_extra is not None
    assert field_info.json_schema_extra["pattern"] == regex_helpers.EMAIL
