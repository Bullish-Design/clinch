# src/clinch/examples/echo.py
from __future__ import annotations

from clinch import Field
from clinch.base import BaseCLICommand, BaseCLIResponse, CLIWrapper
from clinch.parsing import ParsingResult


class EchoResponse(BaseCLIResponse):
    """Parsed response from the echo example."""
    value: str = Field(pattern=r"value=(\w+)")


class EchoCommand(BaseCLICommand):
    """Command object representing `echo "value=<value>"`."""

    # Not used directly by the shell, but kept for clarity / docs
    subcommand = "echo-value"
    response_model = EchoResponse

    value: str

    def build_args(self) -> list[str]:
        # CLIWrapper will run: `echo value=<value>`
        return [f"value={self.value}"]


class EchoWrapper(CLIWrapper):
    """Wrapper around the system `echo` command for examples."""

    command = "echo"

    def echo_value(self, value: str) -> EchoResponse:
        """Echo a value and parse it via EchoResponse.

        This demonstrates using BaseCLICommand + execute_command.
        """
        command = EchoCommand(value=value)
        result: ParsingResult[EchoResponse] = self.execute_command(command)
        # Tests expect a single parsed EchoResponse
        return result.successes[0]
