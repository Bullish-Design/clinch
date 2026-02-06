# src/clinch/examples/ls.py
from __future__ import annotations

from clinch import Field
from clinch.base import BaseCLICommand, BaseCLIResponse, CLIWrapper
from clinch.parsing import ParsingResult


class LSResponse(BaseCLIResponse):
    """Parsed response for a single line of `ls` output."""
    entry: str = Field(pattern=r"(.+)")


class LsCommand(BaseCLICommand):
    """Command object representing `ls [paths...]`."""

    subcommand = "ls"
    response_model = LSResponse

    paths: list[str] | None = None

    def build_args(self) -> list[str]:
        # CLIWrapper will run: `ls` or `ls <paths...>`
        if self.paths:
            return list(self.paths)
        return []


class LsWrapper(CLIWrapper):
    """Wrapper around the system `ls` command for examples."""

    command = "ls"

    def list_entries(self, *paths: str) -> list[str]:
        """List directory entries and return them as plain strings.

        This demonstrates using BaseCLICommand + execute_command.
        """
        cmd_paths = list(paths) if paths else None
        command = LsCommand(paths=cmd_paths)
        result: ParsingResult[LSResponse] = self.execute_command(command)
        return [item.entry for item in result.successes]

