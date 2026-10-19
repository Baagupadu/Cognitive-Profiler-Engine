# ADR 0001: Record architecture decisions

Status: Accepted
Date: 13 Oct 2026

## Context

The brief asks for design decisions to be documented and defended in the final review. Decisions made early (for example, the chunk size or the locking approach) are hard to explain weeks later unless the reasoning is written down when the decision is made.

## Decision

Record every significant decision as a short Markdown file in `docs/adr/`, numbered in order (`0001-…`, `0002-…`). Each ADR has these sections: Status, Context, Decision, Alternatives considered, Consequences.

Status moves from **Proposed** (waiting for review) to **Accepted**, and later to **Superseded by ADR-XXXX** if the decision changes. An accepted ADR is never edited to reverse its decision. A new ADR replaces it instead.

## Alternatives considered

- **Decisions only inside the TDD:** this loses the history of why something changed.
- **Decisions in PR descriptions:** these are hard to find later and not reviewed as design.

## Consequences

Every PR that changes the design adds or updates an ADR. The TDD links to the ADRs instead of repeating them.
