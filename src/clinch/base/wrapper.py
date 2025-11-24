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

    def _build_positional_args(self, *args: Any) -> list[str]:
        return [str(arg) for arg in args]

    def _build_args(self, **kwargs: Any) -> list[str]:
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
        positional_args = self._build_positional_args(*args)
        keyword_args = self._build_args(**kwargs)
        cli_args: list[str] = [*positional_args, *keyword_args]
        command_str = self._build_command_string(cli_args)

        try:
            cmd = _sh.Command(self.command)
            result = cmd(
                *cli_args,
                _timeout=self.timeout,
                _err_to_out=False,
            )
        except Exception as exc:  # pragma: no cover
            CommandNotFound = getattr(_sh, "CommandNotFound", type(exc))
            TimeoutException = getattr(_sh, "TimeoutException", type(exc))
            ErrorReturnCode = getattr(_sh, "ErrorReturnCode", type(exc))

            if isinstance(exc, CommandNotFound):
                raise CommandNotFoundError(str(exc)) from exc

            if isinstance(exc, TimeoutException):
                raise TimeoutError(
                    f"Command '{command_str}' timed out after {self.timeout} seconds"
                ) from exc

            if isinstance(exc, ErrorReturnCode):
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
        result: ParsingResult[TResponse] = response_model.parse_output(preprocessed)
        if self.strict_mode and result.has_failures:
            raise ParsingError(result.failures)
        return result
