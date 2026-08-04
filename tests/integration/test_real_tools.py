# tests/integration/test_real_tools.py
from __future__ import annotations

import shutil

import pytest

from clinch import BaseCLIError, Field
from clinch.base import BaseCLIResponse, CLIWrapper


class EchoResponse(BaseCLIResponse):
    value: str = Field(pattern=r"value=(\w+)")


class EchoWrapper(CLIWrapper):
    command = "echo"


class LSResponse(BaseCLIResponse):
    entry: str = Field(pattern=r"(.+)")


class LsWrapper(CLIWrapper):
    command = "ls"


def test_echo_integration_parses_value() -> None:
    wrapper = EchoWrapper()
    result = wrapper._execute("value=test", response_model=EchoResponse)

    assert result.success_count == 1
    assert result.failure_count == 0
    assert result.successes[0].value == "test"


def test_ls_integration_produces_entries() -> None:
    wrapper = LsWrapper()
    result = wrapper._execute(response_model=LSResponse)

    assert result.success_count >= 1
    assert result.failure_count == 0


def test_ls_integration_nonexistent_path_raises_error_model() -> None:
    wrapper = LsWrapper()
    try:
        wrapper._execute("/definitely/nonexistent/path/for/clinch", response_model=LSResponse)
    except BaseCLIError as exc:
        assert "ls" in exc.command
        assert exc.exit_code != 0
    else:
        raise AssertionError("Expected BaseCLIError to be raised for nonexistent path")


class GitBranchResponse(BaseCLIResponse):
    name: str = Field(pattern=r"\*?\s+(\S+)")
    is_current: bool = Field(default=False, pattern=r"(\*)")


class GitWrapper(CLIWrapper):
    command = "git"

    def branches(self):
        return self._execute("branch", response_model=GitBranchResponse)


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_git_branch_integration_captures_output_despite_tty_pager() -> None:
    """Regression: ``git branch`` auto-pages on a TTY, which broke capture.

    sh's default ``tty_out=True`` makes git detect a terminal and spawn
    ``less``; CLInch must capture through a pipe so parsing succeeds.
    """
    result = GitWrapper().branches()

    assert result.success_count >= 1
    assert result.failure_count == 0
    assert any(b.name == "main" for b in result.successes)
