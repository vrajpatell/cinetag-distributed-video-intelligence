"""Process bootstrap: load secrets before Settings/DB are first resolved."""

from __future__ import annotations


def ensure_preload() -> None:
    """Preload Secret Manager values into os.environ, then refresh cached Settings."""
    from app.core.config import get_settings
    from app.core.secrets import preload_known_secrets

    preload_known_secrets()
    get_settings.cache_clear()
