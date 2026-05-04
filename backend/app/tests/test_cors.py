from app.core.config import Settings


def test_cors_parsing():
    s = Settings(cors_allowed_origins='https://a.com,https://b.com')
    assert s.cors_origins == ['https://a.com', 'https://b.com']
