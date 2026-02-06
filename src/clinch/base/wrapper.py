# src/clinch/base/wrapper.py
from __future__ import annotations

from typing import Any, ClassVar, TypeVar

import sh
from pydantic import BaseModel, field_validator

from clinch.base.command import BaseCLICommand
from clinch.base.error import BaseCLIError
from clinch.base.response import BaseCLIResponse
from clinch.exceptions import CommandNotFoundError, CommandTimeoutError, ParsingError
from clinch.parsing import ParsingResult

TResponse = TypeVar("TResponse", bound=BaseCLIResponse)


def _to_text(value: Any, encoding: str = "utf-8") -> str:
    """Return value as a text string, decoding bytes if necessary."""
    if isinstance(value, (bytes, bytearray)):
        return value.decode(encoding)
    return str(value)


class CLIWrapper(BaseModel):
    """Base class for wrapping CLI tools.

    Subclasses typically set command and may override strict_mode,
    timeout, or provide a custom error_model.  Command execution is
    implemented via sh.
    """

    # Required: underlying CLI command
    command: ClassVar[str]

    # Error model used when exit code is non-zero
    error_model: ClassVar[type[BaseCLIError]] = BaseCLIError

    # Runtime configuration
    strict_mode: bool = False
    timeout: int = 30
    encoding: str = "utf-8"

    model_config = {
        "arbitrary_types_allowed": True,
        "extra": "forbid",
        "validate_assignment": True,
        "validate_default": True,
    }

    @field_validator("timeout")
    @classmethod
    def _validate_timeout(cls, value: int) -> int:
        """Ensure timeout is positive and not unreasonably large."""
        if value <= 0:
            raise ValueError("timeout must be positive")
        if value > 600:
            raise ValueError("timeout must not exceed 600 seconds")
        return value

    def model_post_init(self, __context: Any) -> None:  # type: ignore[override]
        """Validate wrapper configuration after initialization."""
        if not getattr(type(self), "command", None):
            msg = f"{type(self).__name__} must define 'command' class variable"
            raise TypeError(msg)

    # ------------------------------------------------------------------
    # Argument building hooks
    # ------------------------------------------------------------------

    def _build_positional_args(self, *args: Any) -> list[str]:
        """Convert positional arguments to their string representations."""
        return [str(arg) for arg in args]

    def _build_args(self, **kwargs: Any) -> list[str]:
        """Convert keyword arguments into a flat list of CLI arguments.

        * None values are skipped.
        * Boolean True -> ``--flag``, False -> omitted.
        * List values are expanded: ``exclude=['a', 'b']`` becomes
          ``--exclude a --exclude b``.
        * Other values become ``--key value``.
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

        * Stripping ANSI color codes.
        * Removing headers or footers.
        * Normalizing whitespace or line endings before parsing.
        """
        return output

    def _get_error_model(self) -> type[BaseCLIError]:
        """Return the error model class used for failures."""
        return self.error_model

    def _build_command_string(self, args: list[str]) -> str:
        """Return a human-readable command string for error messages."""
        parts = [self.command, *args]
        return " ".join(parts)

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    def _execute(
        self,
        *args: Any,
        response_model: type[TResponse],
        stdin: str | bytes | None = None,
        **kwargs: Any,
    ) -> ParsingResult[TResponse]:
        """Execute the CLI command and parse its output.

        Parameters
        ----------
        *args:
            Positional arguments passed to the CLI command.
        response_model:
            The BaseCLIResponse subclass used to parse stdout.
        stdin:
            Optional data to send to the command's standard input.
        **kwargs:
            Keyword arguments converted to CLI flags via ``_build_args``.
        """
        positional_args = self._build_positional_args(*args)
        keyword_args = self._build_args(**kwargs)
        cli_args: list[str] = [*positional_args, *keyword_args]
        command_str = self._build_command_string(cli_args)

        sh_kwargs: dict[str, Any] = {
            "_timeout": self.timeout,
            "_err_to_out": False,
        }
        if stdin is not None:
            sh_kwargs["_in"] = stdin

        try:
            cmd = sh.Command(self.command)
            result = cmd(*cli_args, **sh_kwargs)
        except sh.CommandNotFound as exc:
            raise CommandNotFoundError(str(exc)) from exc
        except sh.TimeoutException as exc:
            raise CommandTimeoutError(
                f"Command '{command_str}' timed out after {self.timeout} seconds"
            ) from exc
        except sh.ErrorReturnCode as exc:
            exit_code = exc.exit_code
            stdout_text = _to_text(exc.stdout, self.encoding)
            stderr_text = _to_text(exc.stderr, self.encoding)

            error_cls = self._get_error_model()
            error = error_cls(
                command=command_str,
                exit_code=exit_code,
                stderr=stderr_text,
                stdout=stdout_text,
            )
            raise error from exc

        stdout_value = getattr(result, "stdout", result)
        stdout_text = _to_text(stdout_value, self.encoding)
        preprocessed = self._preprocess_output(stdout_text)
        parse_result: ParsingResult[TResponse] = response_model.parse_output(preprocessed)

        if self.strict_mode and parse_result.has_failures:
            raise ParsingError(parse_result.failures)

        return parse_result

    # ------------------------------------------------------------------
    # Async execution
    # ------------------------------------------------------------------

    async def _execute_async(
        self,
        *args: Any,
        response_model: type[TResponse],
        stdin: str | bytes | None = None,
        **kwargs: Any,
    ) -> ParsingResult[TResponse]:
        """Execute the CLI command asynchronously and parse its output.

        Uses ``asyncio.create_subprocess_exec`` for non-blocking execution.
        The interface mirrors :meth:`_execute`.
        """
        import asyncio

        positional_args = self._build_positional_args(*args)
        keyword_args = self._build_args(**kwargs)
        cli_args: list[str] = [*positional_args, *keyword_args]
        command_str = self._build_command_string(cli_args)

        stdin_bytes: bytes | None = None
        if isinstance(stdin, str):
            stdin_bytes = stdin.encode(self.encoding)
        elif isinstance(stdin, bytes):
            stdin_bytes = stdin

        try:
            proc = await asyncio.create_subprocess_exec(
                self.command,
                *cli_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE if stdin_bytes is not None else None,
            )
            stdout_raw, stderr_raw = await asyncio.wait_for(
                proc.communicate(input=stdin_bytes),
                timeout=self.timeout,
            )
        except FileNotFoundError as exc:
            raise CommandNotFoundError(str(exc)) from exc
        except TimeoutError as exc:
            proc.kill()
            await proc.wait()
            raise CommandTimeoutError(
                f"Command '{command_str}' timed out after {self.timeout} seconds"
            ) from exc

        stdout_text = stdout_raw.decode(self.encoding) if stdout_raw else ""
        stderr_text = stderr_raw.decode(self.encoding) if stderr_raw else ""

        if proc.returncode and proc.returncode != 0:
            error_cls = self._get_error_model()
            error = error_cls(
                command=command_str,
                exit_code=proc.returncode,
                stderr=stderr_text,
                stdout=stdout_text,
            )
            raise error

        preprocessed = self._preprocess_output(stdout_text)
        parse_result: ParsingResult[TResponse] = response_model.parse_output(preprocessed)

        if self.strict_mode and parse_result.has_failures:
            raise ParsingError(parse_result.failures)

        return parse_result

    # ------------------------------------------------------------------
    # Command-object execution
    # ------------------------------------------------------------------

    def execute_command(self, command: BaseCLICommand) -> ParsingResult[Any]:
        """Execute a BaseCLICommand instance via this wrapper."""
        args = command.build_args()
        response_model = command.get_response_model()
        return self._execute(*args, response_model=response_model)

    async def execute_command_async(self, command: BaseCLICommand) -> ParsingResult[Any]:
        """Execute a BaseCLICommand instance asynchronously."""
        args = command.build_args()
        response_model = command.get_response_model()
        return await self._execute_async(*args, response_model=response_model)
