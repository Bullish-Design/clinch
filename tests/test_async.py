# tests/test_async.py
from __future__ import annotations

import pytest

from clinch import BaseCLIError, CommandNotFoundError, CommandTimeoutError, Field
from clinch.base import BaseCLIResponse, CLIWrapper


class EchoResponse(BaseCLIResponse):
    value: str = Field(pattern=r"value: (\w+)")


class EchoWrapper(CLIWrapper):
    command = "echo"


class CatResponse(BaseCLIResponse):
    line: str = Field(pattern=r"(.+)")


class CatWrapper(CLIWrapper):
    command = "cat"


@pytest.mark.asyncio
async def test_execute_async_success() -> None:
    wrapper = EchoWrapper()
    result = await wrapper._execute_async("value: hello", response_model=EchoResponse)
    assert result.success_count == 1
    assert result.successes[0].value == "hello"


@pytest.mark.asyncio
async def test_execute_async_command_not_found() -> None:
    class MissingWrapper(CLIWrapper):
        command = "definitely-missing-command-xyz123"

    wrapper = MissingWrapper()
    with pytest.raises(CommandNotFoundError):
        await wrapper._execute_async("test", response_model=EchoResponse)


@pytest.mark.asyncio
async def test_execute_async_timeout() -> None:
    class SleepWrapper(CLIWrapper):
        command = "sleep"
        timeout: int = 1

    wrapper = SleepWrapper()
    with pytest.raises(CommandTimeoutError):
        await wrapper._execute_async("10", response_model=EchoResponse)


@pytest.mark.asyncio
async def test_execute_async_non_zero_exit() -> None:
    class LsWrapper(CLIWrapper):
        command = "ls"

    wrapper = LsWrapper()
    with pytest.raises(BaseCLIError):
        await wrapper._execute_async("/nonexistent/path/xyz", response_model=EchoResponse)


@pytest.mark.asyncio
async def test_execute_async_with_stdin() -> None:
    wrapper = CatWrapper()
    result = await wrapper._execute_async(response_model=CatResponse, stdin="hello async")
    assert result.success_count == 1
    assert result.successes[0].line == "hello async"


@pytest.mark.asyncio
async def test_execute_async_strict_mode() -> None:
    from clinch import ParsingError

    class StrictWrapper(CLIWrapper):
        command = "echo"
        strict_mode: bool = True

    wrapper = StrictWrapper()
    with pytest.raises(ParsingError):
        await wrapper._execute_async("invalid line", response_model=EchoResponse)
