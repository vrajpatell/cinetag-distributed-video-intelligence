from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.catalog.comparison import Comparison, compare
from app.catalog.dataset import Dataset
from app.catalog.distribution import distribution
from app.catalog.files import MEDIA_TYPES, encode_table
from app.catalog.query import DATASETS, EXPORT_LIMIT, InvalidQuery, breakdown, quality, table
from app.catalog.schema import (
    BreakdownQuery,
    BreakdownResult,
    CatalogSchema,
    DistributionQuery,
    DistributionResult,
    ExportQuery,
    QualityReport,
    TableQuery,
    TableResult,
)
from app.core.auth import RequireViewerOrAbove
from app.db.session import get_db
from app.delivery.manifest import load_manifest

router = APIRouter(prefix="/catalog", tags=["catalog"])
Database = Annotated[Session, Depends(get_db)]


def lookup(dataset: str) -> Dataset:
    entry = DATASETS.get(dataset)
    if not entry:
        raise HTTPException(404, "Unknown catalog dataset")
    return entry


Report = Annotated[Dataset, Depends(lookup)]


@router.get("/schema", response_model=CatalogSchema, operation_id="get_catalog_schema")
def schema(_auth: RequireViewerOrAbove):
    return CatalogSchema(datasets=[d.info() for d in DATASETS.values()], export_limit=EXPORT_LIMIT)


@router.get("/quality", response_model=QualityReport, operation_id="get_quality_report")
def quality_report(db: Database, _auth: RequireViewerOrAbove):
    return quality(db)


@router.post("/{dataset}/query", response_model=TableResult, operation_id="query_dataset")
def query_dataset(query: TableQuery, report: Report, db: Database, _auth: RequireViewerOrAbove):
    try:
        return table(db, report, query)
    except InvalidQuery as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/{dataset}/groups", response_model=BreakdownResult, operation_id="group_dataset")
def group_dataset(query: BreakdownQuery, report: Report, db: Database, _auth: RequireViewerOrAbove):
    try:
        return breakdown(db, report, query)
    except InvalidQuery as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post(
    "/{dataset}/export",
    response_class=Response,
    operation_id="export_dataset",
    responses={
        200: {
            "content": {
                media: {"schema": {"type": "string", "format": "binary"}}
                for media in MEDIA_TYPES.values()
            }
        }
    },
)
def export_dataset(query: ExportQuery, report: Report, db: Database, _auth: RequireViewerOrAbove):
    try:
        result = table(db, report, query, export=True)
    except InvalidQuery as exc:
        raise HTTPException(422, str(exc)) from exc
    name = f"cinetag-{report.key}.{query.format.value}"
    return Response(
        content=encode_table(result, query.format),
        media_type=MEDIA_TYPES[query.format],
        headers={
            "Content-Disposition": f'attachment; filename="{name}"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/compare", response_model=Comparison, operation_id="compare_catalog_videos")
def compare_videos(
    db: Database,
    _auth: RequireViewerOrAbove,
    left: Annotated[int, Query(gt=0)],
    right: Annotated[int, Query(gt=0)],
):
    if left == right:
        raise HTTPException(422, "Select two different videos")
    first = load_manifest(db, left)
    second = load_manifest(db, right)
    if first is None or second is None:
        raise HTTPException(404, "One or both videos are missing")
    return compare(first, second)


@router.post(
    "/{dataset}/distribution", response_model=DistributionResult, operation_id="measure_dataset"
)
def measure_dataset(
    query: DistributionQuery, report: Report, db: Database, _auth: RequireViewerOrAbove
):
    try:
        return distribution(db, report, query)
    except InvalidQuery as exc:
        raise HTTPException(422, str(exc)) from exc
