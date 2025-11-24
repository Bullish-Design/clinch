# tests/test_regex_helpers.py
from __future__ import annotations

import re

from clinch.utils import regex_helpers


def test_semver_pattern_positive_and_negative() -> None:
    pattern = regex_helpers.SEMVER
    assert re.fullmatch(pattern, "1.2.3")
    assert re.fullmatch(pattern, "1.2.3-alpha+build.1")
    assert not re.fullmatch(pattern, "1.2")
    assert not re.fullmatch(pattern, "1.2.3.4")


def test_file_path_pattern_positive_and_negative() -> None:
    pattern = regex_helpers.FILE_PATH
    assert re.fullmatch(pattern, "/usr/local/bin/python")
    assert not re.fullmatch(pattern, "relative/path")
