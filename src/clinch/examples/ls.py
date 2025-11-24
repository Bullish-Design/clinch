# src/clinch/examples/ls.py
from __future__ import annotations

from clinch import Field
from clinch.base import BaseCLIResponse, CLIWrapper
from clinch.parsing import ParsingResult


class LSResponse(BaseCLIResponse):
    entry: str = Field(pattern=r"(.+)", description="Raw entry line from ls output")


class LsWrapper(CLIWrapper):
    command = "ls"

    def list_entries(self, *paths: str) -> list[str]:
        result: ParsingResult[LSResponse] = self._execute(
            *paths,
            response_model=LSResponse,
        )
        return [item.entry for item in result.successes]
