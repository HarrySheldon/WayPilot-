# WayPilot

WayPilot is a personalized travel planning and dynamic adjustment platform.

Project documents:

- `AGENTS.md`: repository instructions for coding agents.
- `plan.md`: overall project plan and MVP phases.
- `agent.md`: WayPilot Agent subsystem design.

## Current Development Status

The project has a persisted MVP vertical slice for trip planning, candidate review, versioning, Agent execution, provider tools, and controlled vector RAG.

Implemented:

- Repository-level agent instructions.
- Project and Agent design documents.
- FastAPI, Docker Compose, Celery, SQLAlchemy Base, Alembic, and pgvector migration scaffolding.
- JWT login flow with persistent users and password hashing.
- Domain and service models for Trip, UserPreference, TripCandidate, TripVersion, rollback, current itinerary projection, conflicts, AgentRun, ToolCall, RAG, and AgentTrace.
- Deterministic conflict detector for time overlap, transfer, opening status, budget, weather, pace, required places, and avoidances.
- Lightweight Agent Runtime with OpenAI-compatible provider adapter, structured output validation, Tool Registry, Candidate creation, Candidate validation, ToolCall recording, RAG retrieval, retry handling, and trace recording.
- Backend API endpoints for auth, users, trips, preferences, candidates, versions, agent generation, agent run lifecycle, events, and tool calls.
- SQLAlchemy repositories for Trip, TripCandidate, TripVersion, current itinerary projection, Preference, AgentRun, ToolCall, RAG, and AgentTrace.
- Configurable repository backend through `REPOSITORY_BACKEND`; `sqlalchemy` enables per-request SQLAlchemy repositories.
- Transaction-wrapped Candidate publish path with rollback coverage when a late write fails.
- Celery task handoff for Agent generation and adjustment.
- Provider interfaces with deterministic seed/mock implementations and Redis-tolerant cache wrappers.
- pgvector-backed RAG ingestion with deterministic test embeddings and user-scoped vector retrieval.
- Frontend login, trip list, trip creation, trip detail, preferences, Agent console, candidate review, version timeline, and agent run details.

Not yet implemented:

- Real provider integrations for maps, weather, transfer time, opening hours, and model calls.
- Live production embedding provider integration.
- Production deployment, observability stack, and browser-level automated UI tests.
- Optional real external APIs for maps, weather, traffic, and opening hours.

## Local Verification

Recommended local dependency setup:

```bash
uv venv --python 3.12 .venv
uv pip install -r backend/requirements-dev.txt
cd frontend
npm install
```

Dependency management conventions:

- Backend runtime dependencies live in `backend/requirements.txt`.
- Backend local/test dependencies live in `backend/requirements-dev.txt`.
- `REPOSITORY_BACKEND=memory` keeps the demo in-memory path; `REPOSITORY_BACKEND=sqlalchemy` uses SQLAlchemy repositories.
- The Python interpreter version is pinned by `.python-version`.
- The frontend dependency lock is `frontend/package-lock.json`; use `npm ci` in CI once the lockfile is committed.
- Generated folders such as `.venv/`, `node_modules/`, `dist/`, and TypeScript build info stay untracked.

Current verification:

```bash
.venv\Scripts\python.exe -B -m pytest
.venv\Scripts\python.exe -c "from backend.app.main import app; print(app.title)"
.venv\Scripts\python.exe -c "import backend.app.models.orm; from backend.app.db.base import Base; print(len(Base.metadata.tables))"
cd backend
..\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head --sql
cd ..\frontend
npm test
npm run build
```

## Docker Compose

Create a local `.env` file for Compose:

```env
DATABASE_URL=postgresql+psycopg://waypilot:waypilot@postgres:5432/waypilot
REPOSITORY_BACKEND=sqlalchemy
REDIS_URL=redis://redis:6379/0
JWT_SECRET_KEY=dev-secret
```

Start the stack:

```bash
docker compose up --build
```

Expected local URLs:

- API docs: http://localhost:8000/docs
- Frontend dev server: http://localhost:5173

Optional seed commands after the backend container is running:

```bash
docker compose exec backend python -m scripts.seed_demo_user
docker compose exec backend python -m scripts.seed_rag_documents
```
