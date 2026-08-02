from __future__ import annotations

import base64
import logging
from functools import lru_cache
from pathlib import Path

import httpx

from app.core.config import settings
from app.ml.mock_embedding_client import MockEmbeddingClient
from app.ml.mock_llm_client import MockLLMClient, parse_with_repair
from app.ml.tag_schema import TagBundle

logger = logging.getLogger(__name__)


class ProviderError(RuntimeError):
    """Raised when a configured external provider fails in strict mode."""


def _openai_client():
    if not settings.openai_api_key:
        return None
    try:
        from openai import OpenAI
    except Exception:
        logger.exception("openai_sdk_unavailable")
        return None
    return OpenAI(api_key=settings.openai_api_key)


def _strict() -> bool:
    return bool(settings.provider_strict)


def _ollama_url(path: str) -> str:
    return f"{settings.ollama_base_url.rstrip('/')}/{path.lstrip('/')}"


def _ollama_chat(prompt: str) -> str:
    schema = TagBundle.model_json_schema()
    response = httpx.post(
        _ollama_url("api/chat"),
        json={
            "model": settings.ollama_llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return only JSON matching the supplied CineTag TagBundle schema. "
                        "Describe only evidence present in the provided metadata and transcript."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "format": schema,
            "stream": False,
            "options": {"temperature": 0.2},
        },
        timeout=settings.ollama_timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    return str((payload.get("message") or {}).get("content") or "{}")


def _ollama_embed(text: str) -> list[float]:
    response = httpx.post(
        _ollama_url("api/embed"),
        json={"model": settings.ollama_embedding_model, "input": text},
        timeout=settings.ollama_timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    embeddings = payload.get("embeddings") or []
    if not embeddings or not embeddings[0]:
        raise ValueError("Ollama returned no embedding")
    return [float(value) for value in embeddings[0]]


def describe_frame(image_bytes: bytes, timestamp_seconds: float) -> str:
    fallback = f"Representative video frame sampled at {timestamp_seconds:.2f}s"
    if settings.vision_provider != "ollama":
        return fallback
    try:
        response = httpx.post(
            _ollama_url("api/chat"),
            json={
                "model": settings.ollama_vision_model,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Describe this video frame in two concise sentences. Include visible "
                            "people, objects, actions, setting, lighting, mood, and any safety-"
                            "relevant content. Do not infer identities or facts not visible."
                        ),
                        "images": [base64.b64encode(image_bytes).decode("ascii")],
                    }
                ],
                "stream": False,
                "options": {"temperature": 0.1},
            },
            timeout=settings.ollama_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        description = str((payload.get("message") or {}).get("content") or "").strip()
        if not description:
            raise ValueError("Ollama vision model returned no description")
        return description[:2000]
    except Exception as exc:
        logger.exception("ollama_vision_failed timestamp=%s", timestamp_seconds)
        if _strict():
            raise ProviderError(f"Ollama vision call failed: {exc}") from exc
        return fallback


@lru_cache(maxsize=4)
def _faster_whisper_model(model_name: str, device: str, compute_type: str):
    from faster_whisper import WhisperModel

    return WhisperModel(model_name, device=device, compute_type=compute_type)


def generate_tag_bundle(prompt: str) -> TagBundle:
    if settings.llm_provider == "ollama":
        try:
            return TagBundle.model_validate_json(_ollama_chat(prompt))
        except Exception as exc:
            logger.exception("ollama_llm_generation_failed")
            if _strict():
                raise ProviderError(f"Ollama LLM call failed: {exc}") from exc

    if settings.llm_provider == "openai":
        client = _openai_client()
        if client is None:
            if _strict():
                raise ProviderError("LLM_PROVIDER=openai but OpenAI client is unavailable")
        else:
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
            except Exception as exc:
                logger.exception("openai_llm_generation_failed")
                if _strict():
                    raise ProviderError(f"OpenAI LLM call failed: {exc}") from exc

    mock = MockLLMClient()
    return parse_with_repair(mock.generate(prompt), mock)


def embed_text(text: str) -> list[float]:
    if settings.embedding_provider == "ollama":
        try:
            return _ollama_embed(text)
        except Exception as exc:
            logger.exception("ollama_embedding_failed")
            if _strict():
                raise ProviderError(f"Ollama embedding call failed: {exc}") from exc

    if settings.embedding_provider == "openai":
        client = _openai_client()
        if client is None:
            if _strict():
                raise ProviderError(
                    "EMBEDDING_PROVIDER=openai but OpenAI client is unavailable"
                )
        else:
            try:
                response = client.embeddings.create(
                    model=settings.openai_embedding_model,
                    input=text,
                )
                return list(response.data[0].embedding)
            except Exception as exc:
                logger.exception("openai_embedding_failed")
                if _strict():
                    raise ProviderError(f"OpenAI embedding call failed: {exc}") from exc

    return MockEmbeddingClient().embed(text)


def transcribe_audio(audio_path: str | None, fallback_text: str) -> tuple[str, float, str]:
    if settings.transcription_provider == "faster_whisper":
        if not (audio_path and Path(audio_path).exists()):
            if _strict():
                raise ProviderError(
                    "TRANSCRIPTION_PROVIDER=faster_whisper but no audio file was extracted"
                )
        else:
            try:
                model = _faster_whisper_model(
                    settings.faster_whisper_model,
                    settings.faster_whisper_device,
                    settings.faster_whisper_compute_type,
                )
                segments, info = model.transcribe(
                    audio_path,
                    beam_size=5,
                    vad_filter=True,
                    language=settings.faster_whisper_language,
                )
                text = " ".join(
                    segment.text.strip() for segment in segments if segment.text.strip()
                )
                if not text:
                    raise ValueError("faster-whisper returned an empty transcript")
                language_probability = float(
                    getattr(info, "language_probability", 0.9) or 0.9
                )
                confidence = min(max(language_probability, 0.0), 1.0)
                return text, confidence, "faster_whisper"
            except Exception as exc:
                logger.exception("faster_whisper_transcription_failed path=%s", audio_path)
                if _strict():
                    raise ProviderError(
                        f"faster-whisper transcription failed: {exc}"
                    ) from exc

    if settings.transcription_provider == "openai":
        if not (audio_path and Path(audio_path).exists()):
            if _strict():
                raise ProviderError(
                    "TRANSCRIPTION_PROVIDER=openai but no audio file was extracted"
                )
        else:
            client = _openai_client()
            if client is None:
                if _strict():
                    raise ProviderError(
                        "TRANSCRIPTION_PROVIDER=openai but OpenAI client is unavailable"
                    )
            else:
                try:
                    with Path(audio_path).open("rb") as audio_file:
                        response = client.audio.transcriptions.create(
                            model=settings.openai_transcription_model,
                            file=audio_file,
                        )
                    text = getattr(response, "text", "") or fallback_text
                    return text, 0.9, "openai"
                except Exception as exc:
                    logger.exception("openai_transcription_failed path=%s", audio_path)
                    if _strict():
                        raise ProviderError(
                            f"OpenAI transcription call failed: {exc}"
                        ) from exc

    return fallback_text, 0.72, "mock"
