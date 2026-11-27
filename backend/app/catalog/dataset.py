"""Map public report field names to trusted SQL expressions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import ColumnElement, Select, select
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.catalog.schema import DatasetInfo, FieldInfo, Kind, Operator, Order, PresetInfo, Sorting


@dataclass(frozen=True)
class Column:
    attr: InstrumentedAttribute
    label: str
    kind: Kind = Kind.text
    groupable: bool = False

    @property
    def key(self) -> str:
        return self.attr.key

    @property
    def measurable(self) -> bool:
        return (
            self.kind not in (Kind.text, Kind.date)
            and self.key != "id"
            and not self.key.endswith("_id")
        )

    def info(self) -> FieldInfo:
        operators = [Operator.equal, Operator.different, Operator.missing, Operator.present]
        if self.kind == Kind.text:
            operators.extend((Operator.contains, Operator.starts_with))
        else:
            operators.extend((Operator.minimum, Operator.maximum))
        return FieldInfo(
            id=self.key,
            label=self.label,
            kind=self.kind,
            operators=operators,
            groupable=self.groupable,
            measurable=self.measurable,
        )


@dataclass(frozen=True)
class Preset:
    key: str
    label: str
    description: str
    expression: Callable[[], ColumnElement[bool]]
    quality: bool = False


@dataclass(frozen=True)
class Dataset:
    key: str
    label: str
    description: str
    model: Any
    video_id: InstrumentedAttribute
    columns: tuple[Column, ...]
    defaults: tuple[str, ...]
    search: tuple[InstrumentedAttribute, ...]
    presets: tuple[Preset, ...]
    sort_key: str = "id"
    sort_order: Order = Order.descending
    joins: tuple[tuple[Any, Any], ...] = field(default_factory=tuple)

    @property
    def by_key(self):
        return {column.key: column for column in self.columns}

    def statement(self, *expressions) -> Select:
        statement = select(*expressions).select_from(self.model)
        for model, condition in self.joins:
            statement = statement.join(model, condition)
        return statement

    def info(self) -> DatasetInfo:
        return DatasetInfo(
            id=self.key,
            label=self.label,
            description=self.description,
            fields=[column.info() for column in self.columns],
            default_columns=list(self.defaults),
            default_sort=Sorting(field=self.sort_key, direction=self.sort_order),
            presets=[
                PresetInfo(id=p.key, label=p.label, description=p.description) for p in self.presets
            ],
        )
