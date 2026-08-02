# Zero-bill, open-source CineTag stack

This is CineTag's default deployment for development, demos, portfolios, and private use. It runs on a machine you already own and does not require cloud credentials or metered AI APIs.

"Free" here means no software license or API usage charges. Hardware, electricity, internet access, backups, and a public domain are still real costs if you choose to operate the system continuously.

## Stack

| Capability | Default | Role |
|------------|---------|------|
| Web UI | Next.js, React, Tailwind CSS | Catalog, upload, jobs, review, search |
| API | FastAPI, SQLAlchemy, Alembic | Control plane and persistence |
| Media tools | FFmpeg and ffprobe | Metadata, frames, audio, scenes, previews |
| LLM runtime | Ollama server | Local model inference over HTTP |
| Tagging model | Qwen2 1.5B Instruct | Structured summaries and tag proposals |
| Vision model | IBM Granite 3.2 Vision 2B | Descriptions of sampled video frames |
| Speech-to-text | faster-whisper, Whisper `small` | Offline transcription on CPU by default |
| Text embeddings | Ollama `all-minilm` | 384-dimensional semantic vectors |
| Database | PostgreSQL 16 with pgvector | Metadata and optional vector indexing |
| Queue | Celery with Valkey | Durable asynchronous pipeline dispatch |
| Media storage | Shared local filesystem volume | Originals, frames, previews, transcripts |
| Packaging | Docker Compose | Reproducible single-machine deployment |

The selected inference components and model weights are available under permissive open-source licenses. Always re-check individual model cards before changing a model or redistributing its weights. FFmpeg licensing depends on how a specific binary was compiled.

License references for the selected defaults:

- [Ollama server — MIT](https://github.com/ollama/ollama/blob/main/LICENSE)
- [Qwen2 1.5B Instruct — Apache-2.0](https://huggingface.co/Qwen/Qwen2-1.5B-Instruct/blob/main/LICENSE)
- [IBM Granite Vision 3.2 2B — Apache-2.0](https://huggingface.co/ibm-granite/granite-vision-3.2-2b)
- [faster-whisper — MIT](https://github.com/SYSTRAN/faster-whisper/blob/master/LICENSE)
- [all-MiniLM-L6-v2 model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [pgvector — PostgreSQL License](https://github.com/pgvector/pgvector/blob/master/LICENSE)
- [Valkey source and license](https://github.com/valkey-io/valkey)

## Hardware profiles

| Profile | Suggested settings | Expected trade-off |
|---------|--------------------|--------------------|
| 8 GB RAM, CPU only | `qwen2:1.5b`, Whisper `base` or `small`, one worker | Slow but usable for short demo clips |
| 16 GB RAM, CPU only | `qwen2:1.5b`, Whisper `small` | Better transcription with moderate latency |
| NVIDIA GPU, 8+ GB VRAM | larger Ollama model, Whisper `small`/`medium`, CUDA compute | Faster processing; requires compatible CUDA libraries |

Start with short videos under five minutes. Video processing time is dominated by transcription and local LLM inference.

## Start the stack

Prerequisites:

- Docker Engine or Docker Desktop with Compose
- At least 15 GB of free disk space for images, models, and sample video
- 8 GB RAM minimum; 16 GB is more comfortable

Run:

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec ollama ollama pull qwen2:1.5b
docker compose exec ollama ollama pull all-minilm
docker compose exec ollama ollama pull granite3.2-vision:2b
make migrate
```

Or use `make up`, `make models`, and `make migrate` for the full sequence.

Open:

- Frontend: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`
- Ollama API: `http://localhost:11434`

The first faster-whisper job downloads the selected Whisper model into the persistent `huggingface_models` volume. Later jobs reuse it.

## Provider configuration

```env
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama
TRANSCRIPTION_PROVIDER=faster_whisper
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_LLM_MODEL=qwen2:1.5b
OLLAMA_EMBEDDING_MODEL=all-minilm
VISION_PROVIDER=ollama
OLLAMA_VISION_MODEL=granite3.2-vision:2b
FASTER_WHISPER_MODEL=small
FASTER_WHISPER_DEVICE=cpu
FASTER_WHISPER_COMPUTE_TYPE=int8
```

Set `PROVIDER_STRICT=true` after the models are installed if jobs should fail instead of falling back to deterministic mock output when local inference is unavailable.

## Semantic-search dimension choice

The historical database migration defines a `vector(1536)` column. The lightweight `all-minilm` model emits 384 dimensions, so the local profile deliberately sets:

```env
SEMANTIC_SEARCH_BACKEND=python
PGVECTOR_ENABLED=false
```

Embeddings are still persisted and semantic search still works through the Python cosine implementation. For a large catalog, add a migration to a 384-dimensional pgvector column before enabling database-side vector search.

## Models are replaceable

- Use a larger, permissively licensed Ollama chat model by changing `OLLAMA_LLM_MODEL` and pulling it first.
- Use a different Ollama embedding model only if the whole catalog is re-embedded and its dimensions match the database strategy.
- Use Whisper `base` for lower memory or `medium` for higher accuracy.
- Review every replacement model's license, redistribution terms, memory needs, and output dimensions.

## Optional cloud paths

The GCP and Vercel documentation remains in the repository as an optional production path. Those managed platforms are not open-source infrastructure and their free tiers have quotas and can change. They are not required for the local stack.
