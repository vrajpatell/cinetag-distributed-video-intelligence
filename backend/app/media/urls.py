"""Signed and local URLs for posters, thumbnails, and preview clips."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import FrameSample, VideoAsset
from app.storage import get_object_store

logger = logging.getLogger(__name__)

_POSTER_URL_TTL_SECONDS = 60 * 60
_PREVIEW_URL_TTL_SECONDS = 60 * 60
_PLAYBACK_URL_TTL_SECONDS = 60 * 60

_NON_PLAYABLE_VIDEO_STATUSES = {"upload_pending", "failed"}


def preview_storage_key(video_id: int) -> str:
    return f"previews/{video_id}/preview.mp4"


def _is_gcs_backend() -> bool:
    return settings.storage_backend == "gcs"


def _signed_or_local_url(
    storage_key: str,
    *,
    request: Request | None,
    route_name: str,
    route_kwargs: dict[str, Any],
    expiration_seconds: int,
) -> str | None:
    store = get_object_store()
    if not store.object_exists(storage_key):
        return None
    try:
        if _is_gcs_backend():
            return store.generate_signed_url(
                storage_key,
                expiration_seconds=expiration_seconds,
                method="GET",
            )
        if request is None:
            return None
        return str(request.url_for(route_name, **route_kwargs))
    except Exception:
        logger.warning(
            "media_url_failed storage_key=%s route=%s",
            storage_key,
            route_name,
            exc_info=True,
        )
        return None


def _frame_urls(
    db: Session,
    video_id: int,
    *,
    request: Request | None,
) -> tuple[str | None, list[str]]:
    frames = (
        db.query(FrameSample)
        .filter_by(video_id=video_id)
        .order_by(FrameSample.timestamp_seconds.asc())
        .all()
    )
    if not frames:
        return None, []

    urls: list[str] = []
    for frame in frames:
        if not frame.storage_key:
            continue
        url = _signed_or_local_url(
            frame.storage_key,
            request=request,
            route_name="frame_stream",
            route_kwargs={"frame_id": frame.id},
            expiration_seconds=_POSTER_URL_TTL_SECONDS,
        )
        if url:
            urls.append(url)

    poster = urls[0] if urls else None
    return poster, urls


def preview_url_for_video(
    video: VideoAsset,
    *,
    request: Request | None,
) -> str | None:
    if video.status in _NON_PLAYABLE_VIDEO_STATUSES:
        return None
    key = preview_storage_key(video.id)
    return _signed_or_local_url(
        key,
        request=request,
        route_name="preview_stream",
        route_kwargs={"video_id": video.id},
        expiration_seconds=_PREVIEW_URL_TTL_SECONDS,
    )


def playback_url_for_video(
    video: VideoAsset,
    *,
    request: Request | None,
) -> str | None:
    if not video.storage_key or video.status in _NON_PLAYABLE_VIDEO_STATUSES:
        return None
    store = get_object_store()
    if not store.object_exists(video.storage_key):
        return None
    try:
        if _is_gcs_backend():
            return store.generate_signed_url(
                video.storage_key,
                expiration_seconds=_PLAYBACK_URL_TTL_SECONDS,
                method="GET",
            )
        if request is None:
            return None
        return str(request.url_for("video_stream", video_id=video.id))
    except Exception:
        logger.exception("playback_url_failed video_id=%s", video.id)
        return None


def media_fields_for_video(
    db: Session,
    video: VideoAsset,
    *,
    request: Request | None,
    include_playback: bool = False,
) -> dict[str, Any]:
    poster_url, thumbnail_urls = _frame_urls(db, video.id, request=request)
    preview_url = preview_url_for_video(video, request=request)
    out: dict[str, Any] = {
        "poster_url": poster_url,
        "thumbnail_urls": thumbnail_urls,
        "preview_url": preview_url,
        "has_preview": preview_url is not None,
    }
    if include_playback:
        out["playback_url"] = playback_url_for_video(video, request=request)
    return out
