from __future__ import annotations

import logging
from pathlib import Path

from app.core.config import settings
from app.ml.mock_embedding_client import MockEmbeddingClient
from app.ml.mock_llm_client import MockLLMClient, parse_with_repair
from app.ml.tag_schema import TagBundle

logger = logging.getLogger(__name__)


def _openai_client():
    if not settings.openai_api_key:
        return None
    try:
        from openai import OpenAI
    except Exception:
        logger.exception("openai_sdk_unavailable")
        return None
    return OpenAI(api_key=settings.openai_api_key)


def generate_tag_bundle(prompt: str) -> TagBundle:
    if settings.llm_provider == "openai":
        client = _openai_client()
        if client is not None:
            try:
                response = client.chat.completions.create(
                    model=settings.openai_llm_model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Return only JSON matching the CineTag TagBundle schema: "
                                "summary, genres, moods, themes, objects, settings, "
                                "content_warnings, marketing_keywords, search_keywords, "
                                "age_suitability {suggested_rating,rationale}, confidence."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                )
                raw = response.choices[0].message.content or "{}"
                return parse_with_repair(raw, MockLLMClient())
            except Exception:
                logger.exception("openai_llm_generation_failed")

    mock = MockLLMClient()
    return parse_with_repair(mock.generate(prompt), mock)


def embed_text(text: str) -> list[float]:
    if settings.embedding_provider == "openai":
        client = _openai_client()
        if client is not None:
            try:
                response = client.embeddings.create(
                    model=settings.openai_embedding_model,
                    input=text,
                )
                return list(response.data[0].embedding)
            except Exception:
                logger.exception("openai_embedding_failed")

    return MockEmbeddingClient().embed(text)


def transcribe_audio(audio_path: str | None, fallback_text: str) -> tuple[str, float, str]:
    if (
        settings.transcription_provider == "openai"
        and audio_path
        and Path(audio_path).exists()
    ):
        client = _openai_client()
        if client is not None:
            try:
                with Path(audio_path).open("rb") as audio_file:
                    response = client.audio.transcriptions.create(
                        model=settings.openai_transcription_model,
                        file=audio_file,
                    )
                text = getattr(response, "text", "") or fallback_text
                return text, 0.9, "openai"
            except Exception:
                logger.exception("openai_transcription_failed path=%s", audio_path)

    return fallback_text, 0.72, "mock"
