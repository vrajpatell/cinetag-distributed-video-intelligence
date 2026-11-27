"""Public contract for the catalog reporting API."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


class Kind(StrEnum):
    text = "text"
    integer = "integer"
    decimal = "decimal"
    date = "datetime"
    duration = "seconds"
    elapsed = "milliseconds"
    size = "bytes"
    confidence = "confidence"


class Operator(StrEnum):
    equal = "eq"
    different = "ne"
    contains = "contains"
    starts_with = "starts_with"
    minimum = "gte"
    maximum = "lte"
    missing = "missing"
    present = "present"


class Order(StrEnum):
    ascending = "asc"
    descending = "desc"


class FileFormat(StrEnum):
    csv = "csv"
    json = "json"
    ndjson = "ndjson"


Identifier = Annotated[str, StringConstraints(min_length=1, max_length=64)]
FilterText = Annotated[str, StringConstraints(max_length=512)]
CellValue = str | int | float | None


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Condition(Input):
    field: Identifier
    operator: Operator
    value: FilterText | None = None

    @model_validator(mode="after")
    def validate_operand(self):
        if self.operator in (Operator.missing, Operator.present):
            if self.value is not None:
                raise ValueError("Presence filters take no value")
        elif self.value is None or not self.value.strip():
            raise ValueError("A filter value is required")
        return self


class Sorting(Input):
    field: Identifier
    direction: Order = Order.ascending


class Selection(Input):
    search: Annotated[str, StringConstraints(strip_whitespace=True, max_length=256)] = ""
    filters: list[Condition] = Field(default_factory=list, max_length=12)
    preset: Identifier | None = None


class TableQuery(Selection):
    columns: list[Identifier] | None = Field(default=None, min_length=1, max_length=32)
    sort: Sorting | None = None
    page: int = Field(default=1, ge=1, le=1_000_000)
    page_size: int = Field(default=25, ge=1, le=100)


class BreakdownQuery(Selection):
    field: Identifier
    limit: int = Field(default=12, ge=1, le=50)


class ExportQuery(TableQuery):
    format: FileFormat = FileFormat.csv


class FieldInfo(BaseModel):
    id: str
    label: str
    kind: Kind
    operators: list[Operator]
    groupable: bool
    measurable: bool


class PresetInfo(BaseModel):
    id: str
    label: str
    description: str


class DatasetInfo(BaseModel):
    id: str
    label: str
    description: str
    fields: list[FieldInfo]
    default_columns: list[str]
    default_sort: Sorting
    presets: list[PresetInfo]


class CatalogSchema(BaseModel):
    datasets: list[DatasetInfo]
    export_limit: int


class ReportRow(BaseModel):
    id: int
    video_id: int | None
    cells: dict[str, CellValue]


class TableResult(BaseModel):
    dataset: str
    columns: list[str]
    rows: list[ReportRow]
    total: int
    page: int
    page_size: int


class Group(BaseModel):
    value: CellValue
    count: int


class BreakdownResult(BaseModel):
    field: str
    groups: list[Group]
    total: int
    remaining: int


class QualityCount(BaseModel):
    dataset: str
    dataset_label: str
    preset: str
    label: str
    description: str
    count: int


class QualityReport(BaseModel):
    checked_at: datetime
    checks: list[QualityCount]


class DistributionQuery(Selection):
    field: Identifier


class DistributionResult(BaseModel):
    field: str
    total: int
    measured: int
    missing: int
    minimum: float | None
    maximum: float | None
    mean: float | None
    median: float | None
    p90: float | None
    p95: float | None
