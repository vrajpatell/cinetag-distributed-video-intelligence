"""Compare saved quality reports by stable dataset and check identifiers."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ValidationError

from app.catalog.schema import QualityReport
from app.catalog_cli.client import CatalogError


class Trend(StrEnum):
    improved = "improved"
    increased = "increased"
    unchanged = "unchanged"
    added = "added"
    removed = "removed"


class Change(BaseModel):
    dataset: str
    preset: str
    label: str
    before: int | None
    after: int | None
    delta: int | None
    trend: Trend


class QualityDiff(BaseModel):
    baseline_time: datetime
    current_time: datetime
    changes: list[Change]

    def has_increases(self):
        return any(change.trend == Trend.increased for change in self.changes)


def load_snapshot(path: Path) -> QualityReport:
    try:
        report = QualityReport.model_validate_json(path.read_bytes())
    except (OSError, ValidationError) as exc:
        raise CatalogError(f"Could not read quality snapshot {path}: {exc}") from exc
    index_checks(report)
    return report


def index_checks(report: QualityReport):
    index = {}
    for check in report.checks:
        key = (check.dataset, check.preset)
        if key in index or check.count < 0:
            raise CatalogError(f"Invalid or duplicate count for {check.dataset}/{check.preset}.")
        index[key] = check
    return index


def diff_reports(baseline: QualityReport, current: QualityReport) -> QualityDiff:
    old = index_checks(baseline)
    new = index_checks(current)
    changes = []
    for dataset, preset in sorted(old.keys() | new.keys()):
        previous = old.get((dataset, preset))
        latest = new.get((dataset, preset))
        before = previous.count if previous else None
        after = latest.count if latest else None
        delta = None if before is None or after is None else after - before
        if previous is None:
            trend = Trend.added
        elif latest is None:
            trend = Trend.removed
        elif delta > 0:
            trend = Trend.increased
        elif delta < 0:
            trend = Trend.improved
        else:
            trend = Trend.unchanged
        changes.append(
            Change(
                dataset=dataset,
                preset=preset,
                label=(latest or previous).label,
                before=before,
                after=after,
                delta=delta,
                trend=trend,
            )
        )
    return QualityDiff(
        baseline_time=baseline.checked_at, current_time=current.checked_at, changes=changes
    )
