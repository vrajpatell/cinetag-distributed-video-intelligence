import json
from app.ml.tag_schema import TagBundle

class MockLLMClient:
    def generate(self, prompt: str) -> str:
        payload = {
            "summary": "A city street interview with upbeat energy.",
            "genres": ["documentary"], "moods": ["energetic"], "themes": ["community"],
            "objects": ["microphone", "camera"], "settings": ["urban street"],
            "content_warnings": [], "marketing_keywords": ["short-form"],
            "search_keywords": ["street interview", "city"],
            "age_suitability": {"suggested_rating": "PG", "rationale": "no explicit content"},
            "confidence": 0.86
        }
        return json.dumps(payload)

def parse_with_repair(raw: str, client: MockLLMClient) -> TagBundle:
    try:
        return TagBundle.model_validate_json(raw)
    except Exception:
        repaired = client.generate("repair")
        return TagBundle.model_validate_json(repaired)
