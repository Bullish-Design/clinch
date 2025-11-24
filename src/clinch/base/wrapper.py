# src/clinch/base/wrapper.py
from __future__ import annotations

import importlib
from typing import Any, ClassVar, List, TypeVar

from pydantic import BaseModel

from clinch.base.error import BaseCLIError
from clinch.base.response import BaseCLIResponse
from clinch.exceptions import CommandNotFoundError, TimeoutError
from clinch.parsing import ParsingResult

TResponse = TypeVar("TResponse", bound=BaseCLIResponse)

_sh = importlib.import_module("sh")


def _to_text(value: Any) -> str:
    if isinstance(value, (bytes, bytearray)):
        return value.decode()
    return str(value)


class CLIWrapper(BaseModel):
    """Base class for wrapping CLI tools."""

    command: ClassVar[str]
    error_model: ClassVar[type[BaseCLIError]] = BaseCLIError

    strict_mode: bool = False
    timeout: int = 30

    model_config = {
        "arbitrary_types_allowed": True,
        "extra": "forbid",
    }

    def _build_args(self, *args: Any, **kwargs: Any) -> List[str]:
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
        return output

    def _get_error_model(self) -> type[BaseCLIError]:

        return self.error_model

    def _build_command_string(self, args: list[str]) -> str:
        parts = [self.command, *args]
        return " ".join(parts)

    def _execute(
        self,
        *args: Any,
        response_model: type[TResponse],
        **kwargs: Any,
    ) -> ParsingResult[TResponse]:
        cli_args = self._build_args(*args, **kwargs)
        command_str = self._build_command_string(cli_args)

        try:
            cmd = _sh.Command(self.command)
            result = cmd(
                *cli_args,
                _timeout=self.timeout,
                _err_to_out=False,
            )
        except Exception as exc:  # pragma: no cover - type-based dispatch
            exc_type = type(exc).__name__

            if exc_type == "CommandNotFound":
                raise CommandNotFoundError(str(exc)) from exc

            if exc_type == "TimeoutException":
                raise TimeoutError(
                    f"Command '{command_str}' timed out after {self.timeout} seconds"
                ) from exc

            if exc_type.startswith("ErrorReturnCode"):
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
        return response_model.parse_output(preprocessed)
