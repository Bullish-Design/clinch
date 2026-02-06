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

    The default :meth:`build_args` implementation automatically converts
    instance fields into CLI flags using the same conventions as
    :meth:`CLIWrapper._build_args`:

    * ``None`` values are skipped.
    * ``bool`` True -> ``--flag``, False -> omitted.
    * ``list`` values are expanded: ``exclude=['a', 'b']`` becomes
      ``--exclude a --exclude b``.
    * Other values become ``--key value``.
    * Underscores in field names are converted to hyphens.

    Override :meth:`build_args` for custom argument formatting.
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

        The default implementation converts all instance fields to CLI
        flags automatically.  Override this to customize argument building.
        """
        args: list[str] = [self.subcommand]

        for field_name in type(self).model_fields:
            value: Any = getattr(self, field_name)

            if value is None:
                continue

            flag = f"--{field_name.replace('_', '-')}"
            if isinstance(value, bool):
                if value:
                    args.append(flag)
            elif isinstance(value, list):
                for item in value:
                    args.extend([flag, str(item)])
            else:
                args.extend([flag, str(value)])

        return args

    def get_response_model(self) -> type[BaseCLIResponse]:
        """Get the response model class used by this command."""
        return self.response_model
