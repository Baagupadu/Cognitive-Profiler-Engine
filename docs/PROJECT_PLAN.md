# Project Plan: Cognitive Profiler Engine

Work breakdown, issue backlog and schedule for BGP-SBX-A-01. The project board on GitHub is the live version of this plan; this file is the baseline.

## Calendar

The programme started on Wed 07 Oct 2026. Weekly status reports and demos are due every Friday.

| Week | Dates | Milestone | Friday report |
|---|---|---|---|
| 1 | 07–13 Oct | M1 Design and data layer | 09 Oct |
| 2 | 14–20 Oct | M1 | 16 Oct |
| 3 | 21–27 Oct | M2 Retrieval and orchestration | 23 Oct |
| 4 | 28 Oct–03 Nov | M2 | 30 Oct |
| 5 | 04–10 Nov | M3 Asynchronous extraction and interface | 06 Nov |
| 6 | 11–17 Nov | M3 | 13 Nov |
| 7 | 18–24 Nov | M4 Model customisation, hardening, final review | 20 Nov |
| 8 | 25 Nov–01 Dec | M4 | 27 Nov |

## Work breakdown

### M1: Design and data layer (Weeks 1–2)

- **Exit condition:** schema, migrations and ingestion merged; TDD v1 approved.
- **Work packages:**
  - project setup: repository, board, templates
  - development environment: Compose, backend skeleton, CI
  - design: TDD v1 and ADRs
  - data layer (D2)
  - ingestion pipeline and chunking report (D3)

### M2: Retrieval and orchestration (Weeks 3–4)

- **Exit condition:** hybrid retrieval evaluated; complete workflow graph with a bounded evaluation loop and tests.
- **Work packages:**
  - semantic search, keyword search and RRF fusion
  - retrieval evaluation harness and report (D4)
  - LLM client interface with fakes
  - LangGraph state and nodes
  - bounded evaluation loop with fallback
  - evaluator test report (D5)

### M3: Asynchronous extraction and interface (Weeks 5–6)

- **Exit condition:** background extractor and streaming UI with the live dashboard working end to end.
- **Work packages:**
  - trait extractor
  - session concurrency control (D6)
  - SSE endpoints
  - Next.js chat and radar chart, with live updates (D7)
  - node-level logging

### M4: Model customisation, hardening, final review (Weeks 7–8)

- **Exit condition:** model serving reproducible; CI green; documentation complete; final presentation delivered.
- **Work packages:**
  - synthetic conversations and dataset curation
  - GGUF model with a Modelfile (D8)
  - latency measurement
  - coverage and failure-path tests
  - security review
  - README, runbook and OpenAPI specification (D9)
  - final TDD
  - presentation (D10)

## Issue backlog

Numbers are the GitHub issue numbers. Items marked "–" are not created yet; GitHub gives them a number when they are.

### M1: Design and data layer

| # | Issue | Priority | Deliverable |
|---|---|---|---|
| 1 | Set up the repo structure | Must | – |
| 2 | Set up branch protection, board and templates | Must | – |
| 3 | Add Docker setup for Postgres with pgvector | Must | – |
| 4 | Create FastAPI backend | Must | – |
| 5 | Add CI checks on pull requests | Must | – |
| 6 | Write design doc V1 | Must | D1 |
| 7 | Write first ADRs | Must | D1 |
| 8 | Create DB tables and first migration (CPE-FR-01) | Must | D2 |
| 9 | Extract text from the corpus PDF (CPE-FR-02) | Must | D3 |
| 10 | Split text into chunks (CPE-FR-02) | Must | D3 |
| – | Create embeddings and save chunks (CPE-FR-02) | Must | D3 |
| – | Write chunking report (CPE-FR-02) | Must | D3 |

Acceptance criteria for M1 (numbered in the same order as the table):

1. **Repository skeleton**
   - Folder layout follows the brief.
   - `.gitignore` excludes `.env`, caches, `node_modules` and model weights.
   - `.env.example` lists every variable, with placeholders only.
   - The README explains how to set up, run and test.
2. **Repository governance**
   - `main` requires a PR, 1 approval and passing CI, and allows squash merges only.
   - The board has the columns Backlog, In Progress, In Review and Done.
   - Milestones M1–M4 and priority labels exist.
   - PR and issue templates are in place.
3. **Compose**
   - `docker compose up -d db` starts PostgreSQL with pgvector available.
   - Credentials come from `.env`, and Compose stops with a clear message if they are missing.
   - The container has a healthcheck, and data is kept in a named volume.
4. **Backend skeleton**
   - FastAPI app factory, with settings validated from the environment.
   - `/health` and `/health/ready` (database and pgvector).
   - JSON logs with a correlation ID for each request.
   - Ruff, mypy (strict) and pytest are configured, and the unit tests pass without a database.
5. **CI**
   - Runs on every PR and on every push to `main`.
   - Runs lint, format check, type check, and tests (unit and integration against a pgvector service) with coverage of at least 70%.
   - Checks that the backend image builds.
6. **TDD v1**
   - Contains the ERD, component diagram, workflow diagram, sequence diagrams and a requirements traceability table.
   - Lists the open questions.
   - Is reviewed by the reviewer.
7. **ADRs**
   - ADR 0001–0007 written with context, decision, alternatives and consequences.
   - Proposed decisions are marked as such.
8. **Models and migration**
   - SQLAlchemy 2.x async models.
   - The first Alembic revision creates the extension, tables, constraints and indexes.
   - An integration test checks the cascade deletes.
   - CI runs an upgrade/downgrade round trip.
9. **Text extraction**
   - Text is extracted per page, with source and page number.
   - Hyphenation and whitespace are cleaned up.
   - Unit tests use a small synthetic PDF.
10. **Chunking**
    - Chunks never split a sentence.
    - Target size and overlap are configurable.
    - Unit tests cover boundaries, overlap and edge cases (empty pages, very long paragraphs).
11. **Embedding and storage**
    - Embeddings are produced through the LLM client interface and stored with document and page metadata.
    - Re-ingesting an unchanged file does nothing (sha256).
    - An integration test uses a fake embedder.
12. **Chunking report**
    - States the chosen size and overlap, with the rationale.
    - Explains the effect on retrieval and on the model's context window.
    - Explains how D4 will validate the choice.

### M2: Retrieval and orchestration

| # | Issue | Deliverable |
|---|---|---|
| – | feat: semantic search with pgvector cosine similarity (CPE-FR-03) | D4 |
| – | feat: keyword search with tsvector and GIN index (CPE-FR-03) | D4 |
| – | feat: Reciprocal Rank Fusion with configurable top-k (CPE-FR-03) | D4 |
| – | test: labelled query set and evaluation harness: recall@5, MRR (CPE-FR-04) | D4 |
| – | docs: retrieval evaluation report | D4 |
| – | feat: LLM client interface, Ollama client and test fakes | D5 |
| – | feat: LangGraph workflow with typed Pydantic state (CPE-FR-05) | D5 |
| – | feat: Intent Router node with conditional edge (CPE-FR-06) | D5 |
| – | feat: Query Formulation node (CPE-FR-07) | D5 |
| – | feat: Generator node with token streaming (CPE-FR-08) | D5 |
| – | feat: Groundedness Evaluator with bounded retries, fallback and recursion limit (CPE-FR-09) | D5 |
| – | test: evaluator test report: at least 10 grounded and ungrounded cases | D5 |

### M3: Asynchronous extraction and interface

| # | Issue | Deliverable |
|---|---|---|
| – | feat: background Trait Extractor with validated JSON and failure isolation (CPE-FR-10) | D6 |
| – | feat: per-session concurrency control with tests (CPE-FR-11) | D6 |
| – | feat: session and message API with SSE streaming (CPE-FR-12) | D7 |
| – | feat: Next.js split-screen layout with chat and radar chart (CPE-FR-13) | D7 |
| – | feat: live radar chart updates over SSE (CPE-FR-14) | D7 |
| – | chore: node-level structured logging and correlation ID in background tasks (NFR-07) | – |

### M4: Model customisation, hardening and final review

| # | Issue | Deliverable |
|---|---|---|
| – | feat: synthetic conversation generator (NFR-04) | D8 |
| – | feat: dataset curation script: 50 conversations to validated JSONL (CPE-FR-15) | D8 |
| – | feat: GGUF model, Modelfile and configurable model via Ollama (CPE-FR-16) | D8 |
| – | test: latency measurement: time to first token and end to end (NFR-02) | D9 |
| – | test: failure-path tests; coverage of at least 70% on backend core (NFR-01, NFR-06) | D9 |
| – | chore: input validation and prompt-injection review (NFR-03) | D9 |
| – | docs: README, runbook, OpenAPI specification, final TDD and ADRs | D9 |
| – | docs: final presentation and demo | D10 |
| – | (Could) feat: re-ranking after fusion, or tracing across nodes (CPE-FR-17) | – |

## Definition of Done

- All Must requirements are implemented and shown end to end.
- Every change is merged to `main` through a reviewed PR, with CI passing.
- Tests cover the evaluation loop, retrieval fusion, concurrency handling and failure paths.
- The D4 and D5 reports are published in `docs/`.
- No secrets, no model weights and no real personal data are in the repository.
- A reviewer can reproduce the system from a clean checkout using only the README.
- The TDD and ADRs match the final implementation.
