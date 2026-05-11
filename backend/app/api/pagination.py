from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Query

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def clamp_page(page: int | None) -> int:
    p = page or 1
    return max(1, p)


def clamp_page_size(page_size: int | None, default: int = DEFAULT_PAGE_SIZE) -> int:
    ps = page_size or default
    return min(max(1, ps), MAX_PAGE_SIZE)


def paginate_sa_query(
    query: Query,
    *,
    page: int | None,
    page_size: int | None,
    default_page_size: int = DEFAULT_PAGE_SIZE,
    max_page_size: int = MAX_PAGE_SIZE,
) -> dict[str, Any]:
    p = clamp_page(page)
    ps = min(max(1, page_size or default_page_size), max_page_size)
    total = query.count()
    items = query.offset((p - 1) * ps).limit(ps).all()
    return {
        "items": items,
        "page": p,
        "page_size": ps,
        "total": total,
        "has_next": p * ps < total,
    }
