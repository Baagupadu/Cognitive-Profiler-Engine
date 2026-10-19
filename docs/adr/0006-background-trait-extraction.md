# ADR 0006: Background trait extraction as an in-process task

Status: Proposed
Date: 13 Oct 2026

## Context

CPE-FR-10 requires the Trait Extractor to run outside the request-response path, and requires that its failures never affect the chat. The review will ask how an extractor failure is contained.

## Decision

- After the assistant answer is stored, the API schedules an asyncio task: `extract_traits(session_id, user_message_id, correlation_id)`.
- The task uses its own database session and runs under a timeout (default 60 s).
- An `asyncio.Semaphore` limits how many extractions run at once (default 2), so a slow local model is not overloaded.
- Every exception is caught at the task boundary and logged with the correlation ID. Nothing is re-raised.
- The model output is validated with Pydantic. Invalid items are dropped.
- Writes are idempotent (`UNIQUE (source_message_id, trait)`), and the task runs `NOTIFY` after it commits.

## Alternatives considered

- **FastAPI `BackgroundTasks`:** tied to the response lifecycle. It gives less direct control over timeouts and concurrency, though it would otherwise work.
- **Job queue** (arq or Celery with Redis): durable, with retries, but adds infrastructure.
- **Job table polled by a worker:** durable without new infrastructure, but needs more code and a worker process.

## Consequences

- Simple, with no extra infrastructure, and failures are isolated by design.
- A job is lost if the process crashes during an extraction. This is acceptable for the sandbox because the next message triggers a new extraction over the recent conversation, so the profile recovers on its own. Moving to a job table is the upgrade path if durability is needed.
