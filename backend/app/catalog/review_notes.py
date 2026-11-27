"""Cross-video editorial notes for triage and handoffs."""

from app.catalog.dataset import Column, Dataset, Preset
from app.catalog.schema import Kind
from app.db.models import ReviewNote, VideoAsset

NOTES = Dataset(
    key="notes",
    label="Review notes",
    description="Find editorial notes across videos and open the asset to resolve them.",
    model=ReviewNote,
    video_id=ReviewNote.video_id,
    columns=(
        Column(ReviewNote.id, "Note ID", Kind.integer),
        Column(ReviewNote.video_id, "Video ID", Kind.integer),
        Column(VideoAsset.title, "Video title"),
        Column(ReviewNote.category, "Category", groupable=True),
        Column(ReviewNote.state, "State", groupable=True),
        Column(ReviewNote.body, "Note"),
        Column(ReviewNote.position_ms, "Position in video", Kind.elapsed),
        Column(ReviewNote.revision, "Revision", Kind.integer),
        Column(ReviewNote.created_at, "Created", Kind.date),
        Column(ReviewNote.updated_at, "Last updated", Kind.date),
    ),
    defaults=("title", "category", "state", "position_ms", "body"),
    search=(VideoAsset.title, ReviewNote.body),
    joins=((VideoAsset, VideoAsset.id == ReviewNote.video_id),),
    sort_key="updated_at",
    presets=(
        Preset(
            "open",
            "Open notes",
            "Notes awaiting an editorial decision.",
            lambda: ReviewNote.state == "open",
        ),
        Preset(
            "timed",
            "Time-specific feedback",
            "Notes attached to a particular position in a video.",
            lambda: ReviewNote.position_ms.is_not(None),
        ),
        Preset(
            "whole_video",
            "Whole-video feedback",
            "Notes applying to an asset as a whole.",
            lambda: ReviewNote.position_ms.is_(None),
        ),
        Preset(
            "resolved",
            "Resolved notes",
            "Review decisions that have been completed.",
            lambda: ReviewNote.state == "resolved",
        ),
    ),
)
