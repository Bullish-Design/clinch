# examples/validated_wrappers.py
from __future__ import annotations

from pydantic import field_validator, model_validator

from clinch import BaseCLICommand, BaseCLIResponse, CLIWrapper, Field
from clinch.parsing import ParsingResult


class GitBranch(BaseCLIResponse):
    """Minimal branch model used for validation examples."""

    name: str = Field(pattern=r"\*?\s+(\S+)")
    is_current: bool = Field(default=False, pattern=r"(\*)")


class GitBranchCommand(BaseCLICommand[GitBranch]):
    """Command object for `git branch` with basic validation."""

    subcommand = "branch"
    response_model = GitBranch

    list_all: bool = False
    max_count: int | None = None

    @field_validator("max_count")
    @classmethod
    def validate_max_count(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 1:
            raise ValueError("max_count must be positive")
        if value > 1000:
            raise ValueError("max_count must not exceed 1000")
        return value

    def build_args(self) -> list[str]:
        args: list[str] = [self.subcommand]
        if self.list_all:
            args.append("--all")
        if self.max_count is not None:
            args.extend(["--max-count", str(self.max_count)])
        return args


class GitWrapper(CLIWrapper):
    """Wrapper using Pydantic validation for configuration."""

    command = "git"
    timeout: int = 30
    default_branch: str = "main"
    protected_branches: set[str] = {"main", "develop"}

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, value: int) -> int:
        # This is in addition to the base-class validator; both will run.
        if value < 5:
            raise ValueError("timeout must be at least 5 seconds for git operations")
        return value

    @model_validator(mode="after")
    def ensure_default_is_protected(self) -> "GitWrapper":
        if self.default_branch not in self.protected_branches:
            msg = "default_branch must be included in protected_branches"
            raise ValueError(msg)
        return self

    def branch(self, *, list_all: bool = False, max_count: int | None = None) -> ParsingResult[GitBranch]:
        command = GitBranchCommand(list_all=list_all, max_count=max_count)
        result: ParsingResult[GitBranch] = self.execute_command(command)
        return result
