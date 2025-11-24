# src/clinch/base/command.py
from __future__ import annotations

from typing import Any, ClassVar, TypeVar

from pydantic import BaseModel

from clinch.base.response import BaseCLIResponse

TResponse = TypeVar("TResponse", bound=BaseCLIResponse)


class BaseCLICommand(BaseModel):
    """Base class for command objects used with CLIWrapper.

    Subclasses typically set:
    * subcommand: the CLI subcommand or initial argument
    * response_model: the BaseCLIResponse subclass used for parsing
    and then declare additional fields for command parameters.
    """

    subcommand: ClassVar[str]
    response_model: ClassVar[type[BaseCLIResponse]]

    model_config = {
        "arbitrary_types_allowed": True,
        "extra": "forbid",
        "validate_assignment": True,
    }

    def build_args(self) -> list[str]:
        """Build CLI arguments from command parameters.

        Override this to customize argument building.
        """
        return [self.subcommand]

    def get_response_model(self) -> type[BaseCLIResponse]:
        """Get the response model class used by this command."""
        return self.response_model
