"""Exact nearest-rank percentiles for filtered numeric columns."""

from __future__ import annotations

import sys

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.catalog.dataset import Dataset
from app.catalog.query import InvalidQuery, clauses, get_column
from app.catalog.schema import DistributionQuery, DistributionResult, Kind


def distribution(db: Session, dataset: Dataset, query: DistributionQuery):
    column = get_column(dataset, query.field)
    if not column.measurable:
        raise InvalidQuery(f"{column.label} is not a measurement")
    # Include all matching rows in the denominator. Treat nonfinite float values as missing.
    attr = column.attr
    value = (
        case((attr.between(-sys.float_info.max, sys.float_info.max), attr), else_=None)
        if column.kind in (Kind.decimal, Kind.duration, Kind.confidence)
        else attr
    )
    values = dataset.statement(value.label("value")).where(*clauses(dataset, query)).subquery()
    ranked = select(
        values.c.value,
        func.row_number().over(order_by=values.c.value.asc().nulls_last()).label("rank"),
        func.count(values.c.value).over().label("measured"),
    ).subquery()

    def percentile(percent):
        # Select the first rank where cumulative coverage reaches this percent.
        target = ranked.c.measured * percent
        match = (ranked.c.rank * 100 >= target) & ((ranked.c.rank - 1) * 100 < target)
        return func.max(case((match, ranked.c.value)))

    row = (
        db.execute(
            select(
                func.count().label("total"),
                func.count(ranked.c.value).label("measured"),
                func.min(ranked.c.value).label("minimum"),
                func.max(ranked.c.value).label("maximum"),
                func.avg(ranked.c.value).label("mean"),
                percentile(50).label("median"),
                percentile(90).label("p90"),
                percentile(95).label("p95"),
            ).select_from(ranked)
        )
        .mappings()
        .one()
    )
    return DistributionResult(field=column.key, missing=row["total"] - row["measured"], **row)
