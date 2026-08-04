# tests/integration/test_root_examples.py
"""Guard the root examples/ scripts against rot.

Each example module is imported and exercised exactly as written, so a
stale pattern, broken API usage, or behavior drift fails here instead of
shipping in an sdist.
"""

from __future__ import annotations

import shutil
from datetime import datetime

import advanced_responses
import pytest
import validated_wrappers
from pydantic import ValidationError

# --- advanced_responses.py --------------------------------------------------


def test_demo_git_branch_parses_and_computes() -> None:
    branches = advanced_responses.demo_git_branch("* main\n  origin/feature-x\n")
    assert len(branches) == 2

    current, remote = branches
    assert current.name == "main"
    assert current.is_current is True
    assert current.short_name == "main"
    assert current.remote is None
    assert current.is_main_branch is True

    assert remote.name == "origin/feature-x"
    assert remote.is_current is False
    assert remote.short_name == "feature-x"
    assert remote.remote == "origin"
    assert remote.is_main_branch is False


def test_demo_log_entries_coerce_and_normalize() -> None:
    entries = advanced_responses.demo_log_entries(
        "2024-03-01 INFO - Started service\n2024-03-01 warn - slow request\n"
    )
    assert len(entries) == 2

    first, second = entries
    assert isinstance(first.timestamp, datetime)
    assert first.level == "INFO"
    assert first.message == "Started service"

    # lowercase input is normalized by the model validator
    assert second.level == "WARN"
    assert second.message == "slow request"


def test_demo_process_usage_anchors_mem_pattern() -> None:
    usage = advanced_responses.demo_process_usage("cpu=12.3 mem=1536")
    assert len(usage) == 1

    item = usage[0]
    assert item.cpu_percent == 12.3
    assert item.memory_mb == 1536  # anchored pattern reads the real value
    assert item.model_dump() == {"cpu_percent": "12.3%", "memory_mb": "1.5 GB"}


# --- validated_wrappers.py --------------------------------------------------


def test_git_branch_command_build_args() -> None:
    command = validated_wrappers.GitBranchCommand(list_all=True, max_count=5)
    assert command.build_args() == ["branch", "--all", "--max-count", "5"]
    assert validated_wrappers.GitBranchCommand().build_args() == ["branch"]


@pytest.mark.parametrize("max_count", [0, 2000])
def test_git_branch_command_rejects_invalid_max_count(max_count: int) -> None:
    with pytest.raises(ValidationError):
        validated_wrappers.GitBranchCommand(max_count=max_count)


def test_git_wrapper_configuration_validation() -> None:
    assert validated_wrappers.GitWrapper().default_branch == "main"

    with pytest.raises(ValidationError):
        validated_wrappers.GitWrapper(timeout=3)  # below the 5s subclass minimum

    with pytest.raises(ValidationError):
        validated_wrappers.GitWrapper(default_branch="feature")  # not protected


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_git_wrapper_branch_integration() -> None:
    result = validated_wrappers.GitWrapper().branch()
    assert result.success_count >= 1
    assert result.failure_count == 0
    assert any(b.name == "main" for b in result.successes)
