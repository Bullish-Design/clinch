# tests/test_fields.py
from __future__ import annotations

from pydantic import BaseModel

from clinch.fields import Field


class TestModel(BaseModel):
    with_pattern: str = Field(pattern=r"test: (\w+)")
    without_pattern: str = Field(default="default")
    with_extra: int = Field(pattern=r"(\d+)", json_schema_extra={"other": "value"})


def test_field_stores_pattern_in_metadata() -> None:
    field_info = TestModel.model_fields["with_pattern"]
    assert field_info.json_schema_extra is not None
    assert field_info.json_schema_extra["pattern"] == r"test: (\w+)"


def test_field_without_pattern_has_no_pattern_metadata() -> None:
    field_info = TestModel.model_fields["without_pattern"]
    if field_info.json_schema_extra is not None:
        assert "pattern" not in field_info.json_schema_extra


def test_field_preserves_existing_json_schema_extra() -> None:
    field_info = TestModel.model_fields["with_extra"]
    assert field_info.json_schema_extra is not None
    assert field_info.json_schema_extra["other"] == "value"
    assert field_info.json_schema_extra["pattern"] == r"(\d+)"


def test_multiple_fields_with_patterns_work() -> None:
    class MultiModel(BaseModel):
        first: str = Field(pattern=r"first: (\w+)")
        second: str = Field(pattern=r"second: (\w+)")

    fields = MultiModel.model_fields
    assert fields["first"].json_schema_extra is not None
    assert fields["second"].json_schema_extra is not None
    assert fields["first"].json_schema_extra["pattern"] == r"first: (\w+)"
    assert fields["second"].json_schema_extra["pattern"] == r"second: (\w+)"


def test_field_works_with_pydantic_model_validation() -> None:
    model = TestModel(with_pattern="value", with_extra=1)
    assert model.with_pattern == "value"
    assert model.without_pattern == "default"
    assert model.with_extra == 1
