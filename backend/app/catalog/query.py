"""Validate report requests and compile bound, dialect-portable SQL queries."""

from __future__ import annotations

import math
from datetime import UTC, datetime

from sqlalchemy import case, false, func, or_
from sqlalchemy.orm import Session

from app.catalog.dataset import Column, Dataset
from app.catalog.library import ASSETS, FRAMES, SCENES, TAGS, TRANSCRIPTS
from app.catalog.operations import EMBEDDINGS, JOBS, STAGES
from app.catalog.review_notes import NOTES
from app.catalog.schema import (
    BreakdownQuery,
    BreakdownResult,
    Condition,
    Group,
    Kind,
    Operator,
    Order,
    QualityCount,
    QualityReport,
    ReportRow,
    Selection,
    TableQuery,
    TableResult,
)

DATASETS = {
    d.key: d for d in (ASSETS, TAGS, SCENES, TRANSCRIPTS, FRAMES, JOBS, STAGES, EMBEDDINGS, NOTES)
}
EXPORT_LIMIT = 2000


class InvalidQuery(ValueError):
    """Input was structurally valid but incompatible with the selected dataset."""


def get_column(dataset: Dataset, key: str) -> Column:
    column = dataset.by_key.get(key)
    if column is None:
        raise InvalidQuery(f"Unknown field '{key}' for {dataset.label}")
    return column


def typed_value(column: Column, raw: str):
    if column.kind == Kind.text:
        return raw
    try:
        if column.kind == Kind.date:
            stamp = datetime.fromisoformat(raw)
            return stamp.astimezone(UTC).replace(tzinfo=None) if stamp.tzinfo else stamp
        if column.kind in (Kind.integer, Kind.size, Kind.elapsed):
            number = int(raw)
            if not -(2**63) <= number < 2**63:
                raise ValueError
            return number
        number = float(raw)
        if not math.isfinite(number):
            raise ValueError
        return number
    except (OverflowError, ValueError) as exc:
        raise InvalidQuery(f"Invalid {column.kind.value} value for {column.label}") from exc


def literal_pattern(raw: str) -> str:
    return raw.replace("!", "!!").replace("%", "!%").replace("_", "!_")


def predicate(dataset: Dataset, condition: Condition):
    column = get_column(dataset, condition.field)
    op = condition.operator
    if op not in column.info().operators:
        raise InvalidQuery(f"{op.value} is unavailable for {column.label}")
    attr = column.attr
    if op in (Operator.missing, Operator.present):
        missing = (
            or_(attr.is_(None), func.trim(attr) == "")
            if column.kind == Kind.text
            else attr.is_(None)
        )
        return missing if op == Operator.missing else ~missing
    value = typed_value(column, condition.value)
    if op == Operator.equal:
        return attr == value
    if op == Operator.different:
        return attr != value
    if op == Operator.minimum:
        return attr >= value
    if op == Operator.maximum:
        return attr <= value
    pattern = literal_pattern(value)
    if op == Operator.contains:
        pattern = "%" + pattern
    return attr.ilike(pattern + "%", escape="!")


def clauses(dataset: Dataset, selection: Selection):
    result = [predicate(dataset, rule) for rule in selection.filters]
    if selection.search:
        pattern = "%" + literal_pattern(selection.search) + "%"
        result.append(or_(false(), *(col.ilike(pattern, escape="!") for col in dataset.search)))
    if selection.preset:
        preset = next((p for p in dataset.presets if p.key == selection.preset), None)
        if not preset:
            raise InvalidQuery(f"Unknown preset for {dataset.label}")
        result.append(preset.expression())
    return result


def cell(value):
    if isinstance(value, datetime):
        aware = value if value.tzinfo else value.replace(tzinfo=UTC)
        return aware.isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def table(db: Session, dataset: Dataset, query: TableQuery, *, export: bool = False) -> TableResult:
    keys = list(query.columns or dataset.defaults)
    if len(set(keys)) != len(keys):
        raise InvalidQuery("Each display column must be unique")
    columns = [get_column(dataset, key) for key in keys]
    sort = query.sort or dataset.info().default_sort
    order_column = get_column(dataset, sort.field).attr
    conditions = clauses(dataset, query)
    total = db.scalar(dataset.statement(func.count()).where(*conditions)) or 0
    if export and total > EXPORT_LIMIT:
        raise InvalidQuery(
            f"Exports support up to {EXPORT_LIMIT} rows. Narrow the selection and retry."
        )
    limit = EXPORT_LIMIT if export else query.page_size
    page = 1 if export else query.page
    statement = dataset.statement(dataset.model.id, dataset.video_id, *(c.attr for c in columns))
    statement = statement.where(*conditions).order_by(
        order_column.desc().nulls_last()
        if sort.direction == Order.descending
        else order_column.asc().nulls_last(),
        dataset.model.id.asc(),
    )
    rows = db.execute(statement.limit(limit + int(export)).offset((page - 1) * limit)).all()
    if export and len(rows) > EXPORT_LIMIT:
        raise InvalidQuery("The selection grew during export. Narrow the selection and retry.")
    return TableResult(
        dataset=dataset.key,
        columns=keys,
        rows=[
            ReportRow(
                id=row[0],
                video_id=row[1],
                cells={key: cell(val) for key, val in zip(keys, row[2:])},
            )
            for row in rows
        ],
        total=total,
        page=page,
        page_size=limit,
    )


def breakdown(db: Session, dataset: Dataset, query: BreakdownQuery) -> BreakdownResult:
    column = get_column(dataset, query.field)
    if not column.groupable:
        raise InvalidQuery(f"{column.label} does not support grouping")
    conditions = clauses(dataset, query)
    bucket = column.attr
    count = func.count()
    grouped = dataset.statement(bucket, count).where(*conditions).group_by(bucket)
    # Window over the grouped counts before LIMIT so the denominator includes the tail.
    groups = db.execute(
        grouped.add_columns(func.sum(count).over())
        .order_by(count.desc(), bucket.asc().nulls_last())
        .limit(query.limit)
    ).all()
    total = int(groups[0][2]) if groups else 0
    return BreakdownResult(
        field=query.field,
        groups=[Group(value=cell(key), count=n) for key, n, _ in groups],
        remaining=total - sum(row[1] for row in groups),
        total=total,
    )


def quality(db: Session) -> QualityReport:
    checks = []
    for dataset in DATASETS.values():
        presets = [p for p in dataset.presets if p.quality]
        if not presets:
            continue
        counts = db.execute(
            dataset.statement(*(func.count(case((p.expression(), 1))) for p in presets))
        ).one()
        for preset, count in zip(presets, counts):
            checks.append(
                QualityCount(
                    dataset=dataset.key,
                    dataset_label=dataset.label,
                    preset=preset.key,
                    label=preset.label,
                    description=preset.description,
                    count=count,
                )
            )
    return QualityReport(checked_at=datetime.now(UTC), checks=checks)
