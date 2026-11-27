from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.auth import RequireViewerOrAbove
from app.db.session import get_db
from app.delivery.formats import SIDECARS, preview, render
from app.delivery.manifest import load_manifest
from app.delivery.schema import DeliveryFormat, DeliveryManifest, DeliveryPreview

router = APIRouter(prefix="/videos/{video_id}/delivery", tags=["delivery"])


def find_manifest(video_id: int, db: Annotated[Session, Depends(get_db)]):
    manifest = load_manifest(db, video_id)
    if manifest is None:
        raise HTTPException(404, "Video not found")
    return manifest


Manifest = Annotated[DeliveryManifest, Depends(find_manifest)]


@router.get("", response_model=DeliveryPreview, operation_id="preview_delivery")
def preview_delivery(_auth: RequireViewerOrAbove, manifest: Manifest):
    return preview(manifest)


@router.get("/manifest", response_model=DeliveryManifest, operation_id="get_delivery_manifest")
def delivery_manifest(_auth: RequireViewerOrAbove, manifest: Manifest):
    return manifest


@router.get(
    "/files/{file_format}",
    response_class=Response,
    operation_id="download_delivery_file",
    responses={
        200: {
            "content": {
                file.mime: {"schema": {"type": "string", "format": "binary"}}
                for file in SIDECARS.values()
            }
        }
    },
)
def download(_auth: RequireViewerOrAbove, manifest: Manifest, file_format: DeliveryFormat):
    try:
        payload = render(manifest, file_format)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    file = SIDECARS[file_format]
    name = f"cinetag-{manifest.media.video_id}-{file.name}"
    return Response(
        content=payload,
        media_type=file.mime,
        headers={
            "Content-Disposition": f'attachment; filename="{name}"',
            "Cache-Control": "no-store",
        },
    )
