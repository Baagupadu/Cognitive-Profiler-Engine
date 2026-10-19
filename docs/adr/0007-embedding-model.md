# ADR 0007: Embedding model

Status: Proposed
Date: 13 Oct 2026

## Context

The brief does not name an embedding model. It has to be chosen before the first migration (D2), because the dimension of the `vector` column is fixed in the schema. The system runs locally, so a hosted API, which needs keys and sends text off the machine, is not a good fit.

## Decision

Use `nomic-embed-text`, served by Ollama. It produces 768-dimensional vectors.

- The column is `vector(768)`, and each chunk stores the model name in `embedding_model`.
- The model expects task prefixes: `search_document: ` for chunks and `search_query: ` for queries.
- Before ingestion starts, the model's licence and version are checked and recorded in `ml/README.md`.

## Alternatives considered

- **`all-MiniLM-L6-v2` (sentence-transformers, 384 dimensions):** small and fast, but it adds PyTorch to the backend image and accepts shorter inputs.
- **`mxbai-embed-large` (1024 dimensions):** possibly more accurate, but slower and larger on local hardware.
- **Hosted embedding APIs:** need credentials, and corpus text leaves the machine.

## Consequences

- Runs through the same Ollama server as the chat model, so there is only one model runtime.
- Changing the model later needs a migration, if the dimension changes, plus re-embedding the whole corpus. The stored `embedding_model` column makes it easy to spot stale rows.
- Retrieval quality is measured in D4. A second model can be compared there if results are weak.
