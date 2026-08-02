from app.core.config import Settings


def test_cors_parsing():
    s = Settings(cors_allowed_origins='https://a.com,https://b.com')
    assert s.cors_origins == ['https://a.com', 'https://b.com']


def test_cors_origin_regex_for_vercel_previews():
    pattern = r"https://cinetag-[a-z0-9-]+-vrajpatells-projects\.vercel\.app"
    s = Settings(cors_allowed_origin_regex=pattern)
    assert s.cors_allowed_origin_regex == pattern
