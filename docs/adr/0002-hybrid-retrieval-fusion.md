# ADR 0002: Hybrid retrieval fusion with Reciprocal Rank Fusion

Status: Proposed
Date: 13 Oct 2026

## Context

CPE-FR-03 combines two ranked lists:
- semantic search: pgvector cosine distance
- keyword search: PostgreSQL full-text search, `ts_rank_cd`

Their scores are on different, incomparable scales. Cosine distance falls between 0 and 2, while `ts_rank_cd` is unbounded and depends on document length. The fused list must favour chunks that rank well in either list, and most of all those that rank well in both.

## Decision

Use Reciprocal Rank Fusion (RRF):

```
score(d) = Σ over lists of 1 / (k + rank(d))
```

- `k = 60` (the value from the original RRF paper)
- 20 candidates from each retriever
- `top_k = 5`
- all three values configurable

A chunk missing from a list gets nothing from that list. Ties are broken by semantic rank.

RRF is implemented as a pure function, `reciprocal_rank_fusion(ranked_lists, k)`, with unit tests.

## Alternatives considered

- **Weighted sum of normalised scores:** needs score normalisation and a tuned weight. It is sensitive to how scores are distributed, and that changes with the corpus and the query.
- **Cascade** (keyword filter first, then semantic re-ranking): misses paraphrased queries that share no keywords with the text.
- **Cross-encoder re-ranking after fusion:** this is the optional CPE-FR-17. It needs an extra model and adds latency. It can be added on top of RRF later.

## Consequences

- No weights to tune, and robust to score scale.
- RRF ignores how confident each retriever was. A barely relevant first result counts the same as a perfect one.
- `k` and the candidate count are checked in the retrieval evaluation (D4). Hybrid must beat both single methods on recall@5 and MRR, or the report explains why it doesn't.
