"""Backfill ``embedding_vector`` from JSON ``embedding`` where dimensions match."""

from __future__ import annotations

import argparse
import logging

from app.bootstrap import ensure_preload
from app.core.config import settings
from app.db.models import EmbeddingRecord
from app.db.session import SessionLocal, get_engine
from app.ml.providers import embed_text
from app.observability.metrics import embedding_backfill_total

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    ensure_preload()
    get_engine()
    p = argparse.ArgumentParser(description="Backfill pgvector column from JSON embeddings")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--video-id", type=int, default=None)
    p.add_argument("--reembed", action="store_true", help="Re-embed from text via current provider")
    args = p.parse_args(argv)

    cfg_dim = settings.embedding_vector_dimension
    copy_updated = 0
    copy_would = 0
    skipped_dim = 0
    reembed_done = 0
    reembed_would = 0
    examined = 0

    db = SessionLocal()
    try:
        q = db.query(EmbeddingRecord)
        if args.video_id is not None:
            q = q.filter(EmbeddingRecord.video_id == args.video_id)
        if args.limit:
            q = q.limit(args.limit)
        for rec in q.all():
            examined += 1
            if rec.embedding_dimension is None and rec.embedding:
                rec.embedding_dimension = len(rec.embedding)
                if not args.dry_run:
                    db.add(rec)
            dim = rec.embedding_dimension or (len(rec.embedding) if rec.embedding else 0)

            if args.reembed and rec.text:
                if args.dry_run:
                    reembed_would += 1
                    continue
                vec = embed_text(rec.text)
                rec.embedding = vec
                rec.embedding_dimension = len(vec)
                rec.embedding_provider = settings.embedding_provider
                rec.embedding_model = (
                    settings.openai_embedding_model
                    if settings.embedding_provider == "openai"
                    else "mock-embedding"
                )
                if len(vec) == cfg_dim:
                    rec.embedding_vector = vec
                else:
                    rec.embedding_vector = None
                db.add(rec)
                reembed_done += 1
                embedding_backfill_total.labels(mode="reembed").inc()
                continue

            if not rec.embedding:
                continue
            if dim != cfg_dim:
                skipped_dim += 1
                continue
            if rec.embedding_vector is not None:
                continue
            if args.dry_run:
                copy_would += 1
                continue
            rec.embedding_vector = list(rec.embedding)
            if rec.embedding_dimension is None:
                rec.embedding_dimension = dim
            db.add(rec)
            copy_updated += 1
            embedding_backfill_total.labels(mode="copy_json").inc()

        if not args.dry_run:
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(
        f"examined={examined} copy_updated={copy_updated} copy_would={copy_would} "
        f"reembed_done={reembed_done} reembed_would={reembed_would} "
        f"skipped_wrong_dim={skipped_dim} dry_run={args.dry_run}"
    )
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(main())
