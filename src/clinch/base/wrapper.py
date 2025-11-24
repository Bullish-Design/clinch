# src/clinch/base/wrapper.py
from __future__ import annotations

import importlib
from typing import Any, ClassVar, TypeVar

from pydantic import BaseModel

from clinch.base.error import BaseCLIError
from clinch.base.response import BaseCLIResponse
from clinch.exceptions import CommandNotFoundError, ParsingError, TimeoutError
from clinch.parsing import ParsingResult

TResponse = TypeVar("TResponse", bound=BaseCLIResponse)

_sh = importlib.import_module("sh")


def _to_text(value: Any) -> str:
    """Return value as a text string, decoding bytes if necessary."""
    if isinstance(value, (bytes, bytearray)):
        return value.decode()
    return str(value)


class CLIWrapper(BaseModel):
    """Base class for wrapping CLI tools.

    Subclasses typically set command and may override strict_mode,
    timeout, or provide a custom error_model. Command execution is
    implemented via sh.
    """

    command: ClassVar[str]
    error_model: ClassVar[type[BaseCLIError]] = BaseCLIError
    strict_mode: ClassVar[bool] = False
    timeout: ClassVar[int] = 30

    model_config = {
        "arbitrary_types_allowed": True,
        "extra": "forbid",
    }

    def _build_positional_args(self, *args: Any) -> list[str]:
        """Convert positional arguments to their string representations."""
        return [str(arg) for arg in args]

    def _build_args(self, **kwargs: Any) -> list[str]:
        """Convert keyword arguments into a flat list of CLI arguments.

        * None values are skipped.
        * Boolean True -> --flag, False -> omitted.
        * List values are expanded: exclude=["a", "b"] becomes
          --exclude a --exclude b.
        * Other values become --key value.
        """
        args: list[str] = []
        for key, value in kwargs.items():
            if value is None:
                continue

            flag = f"--{key.replace('_', '-')}"
            if isinstance(value, bool):
                if value:
                    args.append(flag)
            elif isinstance(value, list):
                for item in value:
                    args.extend([flag, str(item)])
            else:
                args.extend([flag, str(value)])

        return args

    def _preprocess_output(self, output: str) -> str:
        """Hook for normalizing raw stdout before parsing.

        Common use cases include:

        * Stripping ANSI color codes, e.g. using a pattern like
          r"\\x1b[[0-9;]*m" with re.sub.
        * Removing headers or footers that appear before/after real data.
        * Normalizing whitespace or line endings before the parsing engine
          runs.
        """
        return output

    def _get_error_model(self) -> type[BaseCLIError]:
        """Return the error model class used for failures."""
        return self.error_model

    def _build_command_string(self, args: list[str]) -> str:
        """Return a human-readable command string for error messages."""
        parts = [self.command, *args]
        return " ".join(parts)

    def _execute(
        self,
        *args: Any,
        response_model: type[TResponse],
        **kwargs: Any,
    ) -> ParsingResult[TResponse]:
        """Execute the CLI command and parse its output."""
        positional_args = self._build_positional_args(*args)
        keyword_args = self._build_args(**kwargs)
        cli_args: list[str] = [*positional_args, *keyword_args]
        command_str = self._build_command_string(cli_args)

        try:
            cmd = _sh.Command(self.command)
            result = cmd(
                *cli_args,
                _timeout=type(self).timeout,
                _err_to_out=False,
            )
        except Exception as exc:  # pragma: no cover - type-based dispatch
            exc_type = type(exc).__name__

            if exc_type == "CommandNotFound":
                raise CommandNotFoundError(str(exc)) from exc

            if exc_type == "TimeoutException":
                raise TimeoutError(
                    f"Command '{command_str}' timed out after {type(self).timeout} seconds"
                ) from exc

            if exc_type == "ErrorReturnCode" or exc_type.startswith("ErrorReturnCode_"):
                exit_code = getattr(exc, "exit_code", 1)
                stdout_text = _to_text(getattr(exc, "stdout", ""))
                stderr_text = _to_text(getattr(exc, "stderr", ""))

                error_model = self._get_error_model()
                if hasattr(error_model, "parse_from_stderr"):
                    error = error_model.parse_from_stderr(
                        stderr=stderr_text,
                        exit_code=exit_code,
                        command=command_str,
                        stdout=stdout_text,
                    )
                else:
                    error = error_model(
                        exit_code=exit_code,
                        stderr=stderr_text,
                        stdout=stdout_text,
                        command=command_str,
                    )

                raise error from exc

            raise

        stdout_value = getattr(result, "stdout", result)
        stdout_text = _to_text(stdout_value)
        preprocessed = self._preprocess_output(stdout_text)
        parse_result: ParsingResult[TResponse] = response_model.parse_output(preprocessed)
        if type(self).strict_mode and parse_result.has_failures:
            raise ParsingError(parse_result.failures)
        return parse_result
