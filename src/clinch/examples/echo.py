# src/clinch/examples/echo.py
from __future__ import annotations
from typing import ClassVar

from clinch import Field
from clinch.base import BaseCLIResponse, CLIWrapper
from clinch.parsing import ParsingResult


class EchoResponse(BaseCLIResponse):
    value: str = Field(pattern=r"value=(\w+)", description="Extracted value from echo output")


class EchoWrapper(CLIWrapper):
    """Wrapper around the ``echo`` command using strict parsing."""

    command = "echo"
    strict_mode: ClassVar[bool] = True

    def echo_value(self, value: str) -> EchoResponse:
        result: ParsingResult[EchoResponse] = self._execute(
            f"value={value}",
            response_model=EchoResponse,
        )
        return result.successes[0]
