from __future__ import annotations

from types import SimpleNamespace

from app.core.config import settings
from app.ml import providers
from app.ml.mock_llm_client import MockLLMClient


class _Response:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def test_ollama_tagging_requests_structured_output(monkeypatch):
    captured: dict = {}

    def fake_post(url, *, json, timeout):
        captured.update(url=url, json=json, timeout=timeout)
        return _Response(
            {"message": {"content": MockLLMClient().generate("local tagging")}}
        )

    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "provider_strict", True)
    monkeypatch.setattr(settings, "ollama_base_url", "http://ollama:11434")
    monkeypatch.setattr(settings, "ollama_llm_model", "qwen2:1.5b")
    monkeypatch.setattr(providers.httpx, "post", fake_post)

    bundle = providers.generate_tag_bundle("title=Local Film")

    assert bundle.summary
    assert captured["url"] == "http://ollama:11434/api/chat"
    assert captured["json"]["model"] == "qwen2:1.5b"
    assert captured["json"]["stream"] is False
    assert captured["json"]["format"]["type"] == "object"


def test_ollama_embedding_returns_float_vector(monkeypatch):
    def fake_post(url, *, json, timeout):
        assert url == "http://ollama:11434/api/embed"
        assert json == {"model": "all-minilm", "input": "semantic search"}
        return _Response({"embeddings": [[0.1, 0.2, 0.3]]})

    monkeypatch.setattr(settings, "embedding_provider", "ollama")
    monkeypatch.setattr(settings, "provider_strict", True)
    monkeypatch.setattr(settings, "ollama_base_url", "http://ollama:11434")
    monkeypatch.setattr(settings, "ollama_embedding_model", "all-minilm")
    monkeypatch.setattr(providers.httpx, "post", fake_post)

    assert providers.embed_text("semantic search") == [0.1, 0.2, 0.3]


def test_ollama_vision_describes_frame(monkeypatch):
    captured: dict = {}

    def fake_post(url, *, json, timeout):
        captured.update(url=url, json=json, timeout=timeout)
        return _Response(
            {"message": {"content": "A person stands beside a red car at night."}}
        )

    monkeypatch.setattr(settings, "vision_provider", "ollama")
    monkeypatch.setattr(settings, "provider_strict", True)
    monkeypatch.setattr(settings, "ollama_base_url", "http://ollama:11434")
    monkeypatch.setattr(settings, "ollama_vision_model", "granite3.2-vision:2b")
    monkeypatch.setattr(providers.httpx, "post", fake_post)

    description = providers.describe_frame(b"jpeg bytes", 12.5)

    assert description == "A person stands beside a red car at night."
    assert captured["url"] == "http://ollama:11434/api/chat"
    assert captured["json"]["model"] == "granite3.2-vision:2b"
    assert captured["json"]["messages"][0]["images"]


def test_faster_whisper_transcribes_local_audio(monkeypatch, tmp_path):
    audio = tmp_path / "audio.mp3"
    audio.write_bytes(b"test audio")

    class _Model:
        def transcribe(self, path, **kwargs):
            assert path == str(audio)
            assert kwargs["vad_filter"] is True
            segments = iter(
                [SimpleNamespace(text=" hello "), SimpleNamespace(text="world")]
            )
            info = SimpleNamespace(language_probability=0.94)
            return segments, info

    monkeypatch.setattr(settings, "transcription_provider", "faster_whisper")
    monkeypatch.setattr(settings, "provider_strict", True)
    monkeypatch.setattr(providers, "_faster_whisper_model", lambda *_args: _Model())

    text, confidence, provider = providers.transcribe_audio(str(audio), "fallback")

    assert text == "hello world"
    assert confidence == 0.94
    assert provider == "faster_whisper"
