# src/clinch/base/response.py
from __future__ import annotations

from typing import ClassVar, Iterable, TypeVar, cast

from pydantic import BaseModel

from clinch.parsing import ParsingResult

TResponse = TypeVar("TResponse", bound="BaseCLIResponse")


class BaseCLIResponse(BaseModel):
    """Base model for all CLI response types in CLInch."""

    _field_patterns: ClassVar[dict[str, str]] = {}

    @classmethod
    def parse_output(
        cls: type[TResponse],
        output: str | Iterable[str],
    ) -> ParsingResult[TResponse]:
        """Parse CLI output into response instances.

        Step 6 provides a placeholder implementation that always returns
        an empty :class:`ParsingResult`. Later steps will integrate the
        real parsing engine.
        """
        _ = output
        result = cast(ParsingResult[TResponse], ParsingResult())
        return result
