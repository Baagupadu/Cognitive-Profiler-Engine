# ADR 0005: Live dashboard updates over SSE

Status: Proposed
Date: 13 Oct 2026

## Context

CPE-FR-14 requires the radar chart to update without a page reload when new traits are stored, and asks for the choice to be justified. Traits are written by a background task (ADR-0006), possibly in a different worker process from the one serving the browser.

## Decision

- `GET /sessions/{id}/traits/stream` is a Server-Sent Events stream.
- When a client connects, it immediately receives the full current profile.
- After that, it receives a new `profile` event whenever traits are stored.
- The extractor runs `NOTIFY traits_updated, '<session_id>'` after it commits. Each backend process keeps one `LISTEN` connection and passes notifications on to the open streams for that session.
- In the browser, `EventSource` reconnects automatically. Because every connection starts with a full snapshot, an update missed while disconnected does no harm.

## Alternatives considered

- **Polling** (`GET /sessions/{id}/traits` every 2–3 s): the simplest and stateless option. Updates arrive up to one interval late, and many requests return nothing new. This stays as the fallback if SSE causes problems.
- **WebSocket:** two-way, but the dashboard only receives data. It adds connection handling that we don't need.

## Consequences

- Updates arrive almost immediately, and it works across worker processes through PostgreSQL. No extra infrastructure is needed.
- Each open dashboard holds one HTTP connection, and each backend process holds one extra database connection for `LISTEN`.
- Uses the same SSE technique as the chat stream, so there is one streaming approach in the codebase.
