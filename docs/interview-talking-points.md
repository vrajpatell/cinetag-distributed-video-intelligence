1. Async pipeline decouples upload latency from compute-heavy processing.
2. Redis + Celery provides mature retry primitives and visibility.
3. Idempotency is enforced by stage-specific upsert semantics.
4. LLM output validated with Pydantic and repair pass.
5. Horizontal scaling via stateless workers and queue partitioning.
