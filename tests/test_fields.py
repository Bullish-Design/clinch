# tests/test_fields.py
from __future__ import annotations

from pydantic import BaseModel

from clinch import Field


class TestModel(BaseModel):
    value: str = Field(pattern=r"value=(\w+)", description="desc")


def test_field_stores_pattern_in_metadata() -> None:
    field = TestModel.model_fields["value"]
    extra = field.json_schema_extra or {}
    assert extra.get("pattern") == r"value=(\w+)"


def test_field_works_with_pydantic_validation() -> None:
    m = TestModel(value="value=test")
    assert m.value == "value=test"
