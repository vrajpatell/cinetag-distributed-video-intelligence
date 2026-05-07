# Future GCP Queue Options

CineTag currently uses Redis + Celery for asynchronous orchestration. This document evaluates GCP-native queueing/orchestration alternatives for future production evolution.

## 1) Current state: Redis + Celery

Advantages:

- Mature retry semantics and operational familiarity
- Flexible task graph patterns
- Works well in local and cloud environments

Trade-offs:

- Requires explicit Redis reliability/capacity planning
- Less integrated with GCP-native IAM/eventing tooling
- Custom ops burden for high-scale and strict compliance contexts

## 2) Option A: Cloud Tasks

Best for HTTP-invoked task dispatch with explicit retry controls.

Pros:

- Native managed queue with per-task retry and scheduling
- Strong IAM integration
- Good operational simplicity

Cons:

- Not a direct drop-in for Celery worker model
- May require redesign around HTTP task handlers

Use when: workflows are request/response oriented and task fanout is moderate.

## 3) Option B: Pub/Sub

Best for event-driven fanout and decoupled consumers.

Pros:

- High throughput, durable messaging
- Native dead-letter and replay patterns
- Strong integration with Cloud Run/Eventarc

Cons:

- At-least-once semantics require idempotent consumers
- More effort for ordered, stateful multi-stage workflows

Use when: large-scale fanout, multiple downstream consumers, event-first architecture.

## 4) Option C: Workflows + Pub/Sub/Cloud Run Jobs

Best for explicit orchestration/state machine control.

Pros:

- Managed orchestration with visible execution graphs
- Good fit for conditional stage transitions and compensating actions
- Native retries/timeouts per step

Cons:

- Potentially higher orchestration complexity and cost
- Requires redesign from current Celery task-chain model

Use when: strict process visibility/governance is needed.

## 5) Option D: Eventarc-triggered services

Best for reactive event routing across services.

Pros:

- Native event routing from GCP sources
- Easy integration with Cloud Run receivers

Cons:

- Not a full orchestration engine
- Often paired with other systems (Pub/Sub, Workflows)

## 6) Decision matrix (summary)

- **Keep Celery/Redis**: fastest iteration, minimal migration effort.
- **Cloud Tasks**: simplest managed queue for HTTP tasks.
- **Pub/Sub**: best for high-throughput event streaming and fanout.
- **Workflows**: best for explicit orchestration and auditability.

## 7) Recommended migration path

1. Keep Celery in near-term while product surface stabilizes.
2. Introduce an internal task abstraction layer to decouple orchestration API from implementation.
3. Pilot one stage (e.g., `embedding`) on Pub/Sub or Cloud Tasks.
4. Validate reliability, observability, and cost at production-like load.
5. Migrate incrementally by stage family, not big-bang.

## 8) Non-negotiable requirements for any queue choice

- Idempotency keys and exactly-once *effect* semantics
- Dead-letter handling and replay tooling
- Per-stage retry policy with exponential backoff
- Unified trace IDs/log fields across API and workers
- Back-pressure controls to protect SQL/LLM provider dependencies
