# Cognitive Profiler Engine

Baagupadu Intern Sandbox Programme, Project A (BGP-SBX-A-01). Confidential – internal use only.

A user chats with an assistant about daily habits. Answers are grounded in a reference corpus on habit psychology. A background process extracts personality traits with confidence scores and shows them on a live radar chart. Trait outputs are for engineering demonstration only and are not a psychological assessment.

**Status:** Milestone M1 (design and data layer) in progress. See [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md).

## Repository layout

| Path | Contents |
|---|---|
| `backend/` | FastAPI app (later: workflow graph, retrieval, extraction) |
| `frontend/` | Next.js application (from M3) |
| `ml/` | Dataset curation scripts, Modelfile, serving notes (M4) |
| `data/` | Synthetic data and corpus references (no personal data) |
| `docs/` | Technical Design Document, ADRs, reports |
| `tests/` | Unit and integration tests |
| `.github/` | CI workflow, PR and issue templates |

## Prerequisites

- Python 3.11 or newer
- Docker Desktop (on Windows it needs WSL 2)

## Setup

```bash
# 1. Configuration: copy the example and set your own password
cp .env.example .env            # PowerShell: Copy-Item .env.example .env

# 2. Python environment
python -m venv .venv
source .venv/bin/activate       # PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Run

```bash
# Database only (PostgreSQL + pgvector)
docker compose up -d db

# Create or update the database tables
alembic upgrade head

# Backend on your machine, with auto-reload
uvicorn app.main:create_app --factory --reload

# Or everything in containers
docker compose up --build
```

Then open:

- http://localhost:8000/health – liveness
- http://localhost:8000/health/ready – database and pgvector check
- http://localhost:8000/docs – interactive API docs (OpenAPI)

Stop with `docker compose down`. Add `-v` to also delete the database volume.

If port 5432 is already in use (for example by a local PostgreSQL), set `POSTGRES_PORT=5433` in `.env`, and change the port in `DATABASE_URL` to match.

## Test and quality checks

These are the same checks CI runs on every pull request:

```bash
ruff check .            # lint
ruff format --check .   # formatting
mypy                    # static types (strict)
pytest --cov            # all tests; needs the database running
pytest -m "not integration"   # unit tests only, no database needed
```

Integration tests rebuild the database schema, so don't point `DATABASE_URL` at data you want to keep.

## How we work

- `main` is protected. Every change goes through a pull request linked to an issue, needs one approving review and green CI, and is squash-merged.
- Branch names: `type/ISSUE-ID-short-description`, for example `feat/13-semantic-search`.
- Commit messages follow Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`) and reference the issue.
- Never commit `.env`, credentials, model weights or real personal data.

## Documentation

- [Technical Design Document](docs/ARCHITECTURE.md)
- [Architecture Decision Records](docs/adr/)
- [Project plan and backlog](docs/PROJECT_PLAN.md)
