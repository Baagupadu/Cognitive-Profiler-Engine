# ADR 0003: Per-session ordering with a PostgreSQL advisory lock

Status: Proposed
Date: 13 Oct 2026

## Context

CPE-FR-11 says that messages arriving in quick succession within one session must be processed in a defined order. The review will ask what happens when three messages arrive before the first answer is complete.

Without control, two workflows for the same session would read the same history at the same time and answer out of order. The backend may run with more than one worker process, so an in-memory lock would not be enough.

## Decision

Within a session, messages are answered one at a time, in arrival order.

1. On arrival, in a short transaction:
   - lock the session row
   - assign `seq = max(seq) + 1`
   - insert the user message as `pending`
2. Acquire a session-level PostgreSQL advisory lock keyed by the session, with a bounded wait (default 120 s). On timeout, send an SSE `session_busy` error and mark the message `failed`.
3. While holding the lock, proceed only if no earlier message in the session is still `pending`. Otherwise release the lock, wait briefly and retry. This covers waiters that are woken out of order.
4. Run the workflow with the full history, which includes earlier answers. Store the answer, mark the message `answered` and release the lock.

Waiting requests send a `status: queued` event, so the UI can show that the message is queued.

## Alternatives considered

- **In-process `asyncio.Lock` per session:** simple, but only correct with a single worker process.
- **Reject while busy (HTTP 409):** simple, but the message is never processed, which does not meet the requirement.
- **External queue** (Redis with arq, or Celery): durable and scalable, but adds infrastructure that the sandbox doesn't need.

## Consequences

- Correct across worker processes. Session-level advisory locks are released automatically if a connection dies, so a crashed request cannot leave a session locked.
- Each active session holds one database connection while it generates. That is fine at sandbox scale, and the pool size is a documented setting.
- Tested with three concurrent requests (order and history), a lock timeout, and a failure in the middle of the workflow (D6).
