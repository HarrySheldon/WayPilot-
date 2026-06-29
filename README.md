# WayPilot

WayPilot is a personalized travel planning and dynamic adjustment platform.

Project documents:

- `AGENTS.md`: repository instructions for coding agents.
- `plan.md`: overall project plan and MVP phases.
- `agent.md`: WayPilot Agent subsystem design.

## Current Development Status

The project has an MVP vertical slice for all planned phases using in-memory repositories plus SQLAlchemy/Alembic persistence scaffolding.

Implemented:

- Repository-level agent instructions.
- Project and Agent design documents.
- FastAPI, Docker Compose, Celery, SQLAlchemy Base, Alembic, and pgvector migration scaffolding.
- JWT-compatible HMAC token service for the authentication boundary.
- Domain and service models for Trip, UserPreference, TripCandidate, TripVersion, rollback, current itinerary projection, conflicts, AgentRun, ToolCall, RAG, and AgentTrace.
- Deterministic conflict detector for time overlap, transfer, opening status, budget, weather, pace, required places, and avoidances.
- Lightweight Agent Runtime with Provider interface, structured output validation, Tool Registry, Candidate creation, Candidate validation, ToolCall recording, RAG retrieval, and trace recording.
- Backend API endpoints for trips, preferences, candidates, versions, and agent runs.
- Frontend pages for trip list, trip creation, trip detail, preferences, candidate review, version history, and agent run details.

Not yet implemented:

- SQLAlchemy repository implementations replacing the in-memory repositories.
- Real JWT login endpoint and password hashing flow wired to persistent users.
- Real provider integrations for maps, weather, transfer time, opening hours, and model calls.
- Real embedding generation and vector similarity search.
- Installed dependency verification, FastAPI runtime test, Alembic migration execution, Vite build, and browser QA.

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
npm run build
```
