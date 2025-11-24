# src/clinch/base/wrapper.py
from __future__ import annotations

from typing import Any, ClassVar, Dict, List, TypeVar

from pydantic import BaseModel

from clinch.base.error import BaseCLIError
from clinch.base.response import BaseCLIResponse
from clinch.parsing import ParsingResult

TResponse = TypeVar("TResponse", bound=BaseCLIResponse)


class CLIWrapper(BaseModel):
    """Base class for wrapping CLI tools.

    Subclasses typically set :attr:`command` and may override
    :attr:`strict_mode`, :attr:`timeout`, or provide a custom
    :attr:`error_model`. This foundation focuses on configuration and
    helper methods; concrete command execution is introduced in Step 11.
    """

    # Name of the CLI command to invoke, e.g. "git" or "docker".
    command: ClassVar[str]

    # Error model used when the CLI command fails.
    error_model: ClassVar[type[BaseCLIError]] = BaseCLIError

    # Whether parsing failures should raise ParsingError in higher-level APIs.
    strict_mode: bool = False

    # Default timeout (in seconds) for command execution.
    timeout: int = 30

    model_config = {
        "arbitrary_types_allowed": True,
        "extra": "forbid",
    }

    def _build_args(self, *args: Any, **kwargs: Any) -> List[str]:
        """Convert Python arguments into a flat list of CLI arguments.

        The default implementation is intentionally simple and
        conservative; it will be enhanced in later steps but should
        remain backwards compatible.

        - Positional arguments are converted to ``str`` and preserved
          in order.
        - Keyword arguments are converted to ``--kebab-case`` flags:
          - ``True`` → ``--flag``
          - ``False`` / ``None`` → omitted
          - other values → ``--flag value``
        """
        cli_args: List[str] = [str(arg) for arg in args]

        for key, value in kwargs.items():
            if value is None:
                continue

            flag = f"--{key.replace('_', '-')}"
            if isinstance(value, bool):
                if value:
                    cli_args.append(flag)
                continue

            cli_args.append(flag)
            cli_args.append(str(value))

        return cli_args

    def _preprocess_output(self, output: str) -> str:
        """Hook for normalizing raw stdout before parsing.

        Subclasses can override this to strip control codes, headers,
        or perform other cleanup. The default implementation is a
        no-op and returns *output* unchanged.
        """
        return output

    def _get_error_model(self) -> type[BaseCLIError]:
        """Return the error model class used for failures."""
        return self.error_model

    def _execute(
        self,
        *args: Any,
        response_model: type[TResponse],
        **kwargs: Any,
    ) -> ParsingResult[TResponse]:
        """Execute the CLI command and parse its output.

        Step 10 only defines the interface and configuration. The
        concrete implementation that calls the underlying command via
        :mod:`sh` is provided in Step 11.
        """
        raise NotImplementedError("Command execution is implemented in Step 11.")
