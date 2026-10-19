# ADR 0004: Streaming and groundedness evaluation

Status: Proposed. Needs the reviewer's confirmation.
Date: 13 Oct 2026

## Context

Two requirements pull in different directions:
- CPE-FR-08: the Generator streams tokens to the client.
- CPE-FR-09: the Groundedness Evaluator rejects ungrounded answers and makes the Generator retry.

The evaluator needs the complete answer. If tokens are streamed while they are generated, the user has already read the answer before it can be rejected.

## Decision (proposed)

- **Retrieval route:**
  - The Generator produces the draft without sending it to the client.
  - The Evaluator checks the draft.
  - Only the approved answer, or the fallback answer, is streamed to the client as `token` events.
  - While the client waits, it receives `status` events (`retrieving`, `generating`, `checking_sources`) so the UI can show progress.
- **Conversational route:** there is no context to evaluate, so tokens stream live as they are generated.

## Alternatives considered

- **Stream live, then send a `replace` event if the answer is rejected:** the first token arrives sooner, but the user briefly sees ungrounded text. That defeats the purpose of the grounding check.
- **Evaluate sentence by sentence while streaming:** much more complex, needs many evaluator calls, and a sentence can only be judged with its context.

## Consequences

- No rejected text ever reaches the user.
- On the retrieval route the first token arrives later, because it includes generation and evaluation time. Time to first token is reported separately for each route (NFR-02).
- For the retrieval route, the "streaming" means sending the approved text in pieces. Generation itself is not shown live. This is stated openly in the TDD and the demo.
