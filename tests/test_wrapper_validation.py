# tests/test_wrapper_validation.py
from __future__ import annotations

import pytest
from pydantic import ValidationError, field_validator, model_validator

from clinch.base import CLIWrapper


def test_port_validation() -> None:
    """Test port range validation on a wrapper field."""

    class PortWrapper(CLIWrapper):
        command = "tool"
        port: int = 8080

        @field_validator("port")
        @classmethod
        def validate_port(cls, v: int) -> int:
            if not 1 <= v <= 65535:
                raise ValueError("Invalid port")
            return v

    # Valid ports work
    PortWrapper(port=1)
    PortWrapper(port=65535)

    # Too low
    with pytest.raises(ValidationError, match="Invalid port"):
        PortWrapper(port=0)

    # Too high
    with pytest.raises(ValidationError, match="Invalid port"):
        PortWrapper(port=70000)


def test_secure_wrapper_requires_ssl_for_remote_hosts() -> None:
    """Model validator enforces SSL for non-local hosts."""

    class SecureWrapper(CLIWrapper):
        command = "api-tool"
        host: str
        use_ssl: bool = True

        @model_validator(mode="after")
        def validate_security(self) -> "SecureWrapper":
            if self.host != "localhost" and not self.use_ssl:
                raise ValueError("SSL required")
            return self

    # Localhost without SSL is allowed
    SecureWrapper(host="localhost", use_ssl=False)

    # Remote host without SSL should fail
    with pytest.raises(ValidationError, match="SSL required"):
        SecureWrapper(host="example.com", use_ssl=False)



# # tests/test_wrapper_validation.py
# from __future__ import annotations

# import pytest
# from pydantic import ValidationError, field_validator, model_validator

# from clinch import BaseCLICommand, BaseCLIResponse, CLIWrapper, Field


# class _RegionWrapper(CLIWrapper):
#     """Wrapper that validates its own configuration via field validators."""

#     command = "my-api"
#     region: str = "us-east-1"

#     @field_validator("region")
#     @classmethod
#     def validate_region(cls, value: str) -> str:
#         allowed = {"us-east-1", "eu-west-1"}
#         if value not in allowed:
#             msg = f"unsupported region {value!r}, expected one of {sorted(allowed)}"
#             raise ValueError(msg)
#         return value


# class _GitLikeWrapper(CLIWrapper):
#     """Wrapper using a model-level validator for cross-field checks."""

#     command = "git"
#     default_branch: str = "main"
#     protected_branches: set[str] = {"main", "develop"}

#     @model_validator(mode="after")
#     def ensure_default_is_protected(self) -> "_GitLikeWrapper":
#         if self.default_branch not in self.protected_branches:
#             msg = "default_branch must be included in protected_branches"
#             raise ValueError(msg)
#         return self


# class _MinimalResponse(BaseCLIResponse):
#     value: str = Field(pattern=r"value: (\w+)")


# class _ValidatedCommand(BaseCLICommand[_MinimalResponse]):
#     subcommand = "echo"
#     response_model = _MinimalResponse

#     max_count: int = 10

#     @field_validator("max_count")
#     @classmethod
#     def validate_max_count(cls, value: int) -> int:
#         if value < 1:
#             raise ValueError("max_count must be positive")
#         if value > 1000:
#             raise ValueError("max_count must not exceed 1000")
#         return value


# def test_wrapper_field_validator_rejects_unsupported_region() -> None:
#     # Valid configuration is accepted
#     wrapper = _RegionWrapper(region="eu-west-1")
#     assert wrapper.region == "eu-west-1"

#     # Invalid configuration fails fast with ValidationError
#     with pytest.raises(ValidationError, match="unsupported region"):
#         _RegionWrapper(region="unknown-region")


# def test_wrapper_model_validator_enforces_cross_field_invariants() -> None:
#     # Default configuration should be valid
#     wrapper = _GitLikeWrapper()
#     assert wrapper.default_branch in wrapper.protected_branches

#     # Invalid configuration should raise ValidationError before any commands run
#     with pytest.raises(ValidationError, match="default_branch must be included"):
#         _GitLikeWrapper(default_branch="feature-x", protected_branches={"main"})


# def test_command_field_validator_runs_on_initialisation() -> None:
#     # Valid command configuration
#     valid = _ValidatedCommand(max_count=5)
#     assert valid.max_count == 5

#     # Invalid values are rejected by Pydantic
#     with pytest.raises(ValidationError, match="must be positive"):
#         _ValidatedCommand(max_count=0)

#     with pytest.raises(ValidationError, match="must not exceed 1000"):
#         _ValidatedCommand(max_count=5000)
