import hashlib

class MockEmbeddingClient:
    def embed(self, text: str) -> list[float]:
        h = hashlib.sha256(text.encode()).digest()
        return [b / 255 for b in h[:16]]
