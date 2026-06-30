# WayPilot Next Phases Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish WayPilot from the current persisted MVP into a usable, auditable travel planning platform with real user isolation, provider boundaries, async Agent execution, vector RAG, and a front-end review loop.

**Architecture:** Keep the modular monolith. Backend changes continue to follow API -> Service -> Repository -> Model, with Agent tools calling Service only through ToolRegistry. PostgreSQL remains the source of truth; Redis is used only for cache, temporary Agent state, and Celery broker/backend.

**Tech Stack:** Python, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, pgvector, Redis, Celery, Pytest, React, TypeScript, Vite, Ant Design, TanStack Query.

---

## Current Baseline

Committed baseline:

```text
e1d3302 feat: persist agent audit repositories
```

Verified baseline:

```powershell
.\.venv\Scripts\python.exe -B -m pytest
# 42 passed, 1 warning

$env:DATABASE_URL='postgresql+psycopg://waypilot:waypilot@localhost:5432/waypilot'
$env:REPOSITORY_BACKEND='sqlalchemy'
.\.venv\Scripts\python.exe -m backend.scripts.smoke_agent_persistence
# run completed, candidate ready, tool_calls persisted, trace persisted
```

Known gaps in current docs:

- `README.md` still says SQLAlchemy repositories for Preference, AgentRun, ToolCall, RAG, and AgentTrace are not implemented. They are now implemented and should be documented in Phase 14.
- Frontend has no Vite proxy or auth token handling yet.
- API still uses hard-coded `demo-user`.

Best-practice references to keep aligned during implementation:

- FastAPI OAuth2/JWT security tutorial: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- SQLAlchemy session and transaction docs: https://docs.sqlalchemy.org/en/20/orm/session_transaction.html
- Celery first steps and Redis broker docs: https://docs.celeryq.dev/en/stable/getting-started/first-steps-with-celery.html
- Vite server proxy docs: https://vite.dev/config/server-options.html#server-proxy
- pgvector project docs: https://github.com/pgvector/pgvector

---

## File Structure Plan

Backend files to create:

```text
backend/app/services/auth.py
backend/app/repositories/users.py
backend/app/api/v1/endpoints/auth.py
backend/app/api/v1/endpoints/users.py
backend/app/schemas/auth.py
backend/scripts/seed_demo_user.py

backend/app/providers/base.py
backend/app/providers/seed.py
backend/app/providers/cache.py
backend/app/services/providers.py
backend/app/schemas/providers.py

backend/app/agent/provider_openai_compatible.py
backend/app/agent/message_store.py
backend/app/agent/error_recovery.py

backend/app/worker/tasks.py
backend/app/services/agent_runs.py

backend/app/rag/embeddings.py
backend/app/rag/ingest.py
backend/app/rag/vector_retriever.py
backend/scripts/seed_rag_documents.py
```

Backend files to modify:

```text
backend/app/api/dependencies.py
backend/app/api/router.py
backend/app/core/config.py
backend/app/core/security.py
backend/app/models/orm.py
backend/app/repositories/sqlalchemy.py
backend/app/agent/runtime.py
backend/app/agent/tools.py
backend/app/agent/rag.py
backend/app/worker/celery_app.py
backend/alembic/versions/0001_initial_schema.py only if no deployed DB relies on it; otherwise add 0002 migration
backend/requirements.txt
backend/requirements-dev.txt
README.md
```

Frontend files to create:

```text
frontend/src/auth/session.ts
frontend/src/pages/LoginPage.tsx
frontend/src/pages/AgentConsolePage.tsx
frontend/src/pages/CandidateDiffPage.tsx
frontend/src/components/AppShell.tsx
frontend/src/components/ConflictList.tsx
frontend/src/components/VersionTimeline.tsx
```

Frontend files to modify:

```text
frontend/vite.config.ts
frontend/src/App.tsx
frontend/src/api/client.ts
frontend/src/api/types.ts
frontend/src/pages/TripDetailPage.tsx
frontend/src/pages/CandidateReviewPage.tsx
frontend/src/pages/VersionsPage.tsx
```

---

## Phase 8: Auth And User Boundary

**Purpose:** Replace `demo-user` with real authenticated users before expanding Agent and RAG capabilities.

**Commit target:** `feat: add jwt auth and user boundary`

### Task 8.1: User Repository And Password Hashing

**Files:**

- Create: `backend/app/repositories/users.py`
- Create: `backend/app/services/auth.py`
- Modify: `backend/app/core/security.py`
- Modify: `backend/requirements.txt`
- Test: `backend/tests/services/test_auth_service.py`
- Test: `backend/tests/repositories/test_user_repository.py`

- [ ] **Step 1: Add failing auth service tests**

Write tests for:

```python
def test_register_user_hashes_password_and_rejects_duplicate_email():
    ...

def test_authenticate_user_returns_token_for_valid_password():
    ...

def test_authenticate_user_rejects_invalid_password():
    ...
```

Run:

```powershell
.\.venv\Scripts\python.exe -B -m pytest backend\tests\services\test_auth_service.py
```

Expected:

```text
ImportError or AttributeError for missing AuthService/UserRepository/PasswordHasher
```

- [ ] **Step 2: Add password hashing implementation**

Preferred dependency:

```text
pwdlib[argon2]
```

If dependency install is blocked, use a small adapter interface and a PBKDF2 stdlib implementation for the current commit, then replace with `pwdlib` in a dependency-management commit.

Required interface:

```python
class PasswordHasher:
    def hash(self, password: str) -> str: ...
    def verify(self, password: str, password_hash: str) -> bool: ...
```

- [ ] **Step 3: Add SQLAlchemy user repository**

Repository methods:

```python
class SQLAlchemyUserRepository:
    def save(self, user: User) -> User: ...
    def get(self, user_id: str) -> User | None: ...
    def get_by_email(self, email: str) -> User | None: ...
```

Keep repository data-access only. Duplicate email handling can surface an integrity error, but user-friendly conflict semantics belong in `AuthService`.

- [ ] **Step 4: Run auth repository/service tests**

Run:

```powershell
.\.venv\Scripts\python.exe -B -m pytest backend\tests\services\test_auth_service.py backend\tests\repositories\test_user_repository.py
```

Expected:

```text
all tests pass
```

### Task 8.2: Auth API And Current User Dependency

**Files:**

- Create: `backend/app/api/v1/endpoints/auth.py`
- Create: `backend/app/api/v1/endpoints/users.py`
- Create: `backend/app/schemas/auth.py`
- Modify: `backend/app/api/dependencies.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/api/test_auth_api.py`
- Test: `backend/tests/api/test_user_isolation.py`

- [ ] **Step 1: Add failing API tests**

Required API behavior:

```text
POST /api/v1/auth/login -> 200 { access_token, token_type: "bearer" }
GET /api/v1/users/me with Bearer token -> current user
GET /api/v1/trips without token -> 401
User A cannot read User B trip -> 404
```

Run:

```powershell
.\.venv\Scripts\python.exe -B -m pytest backend\tests\api\test_auth_api.py backend\tests\api\test_user_isolation.py
```

Expected:

```text
404 for missing endpoints or 200 where 401 is expected because demo-user is still hard-coded
```

- [ ] **Step 2: Implement Bearer auth dependency**

Replace:

```python
def get_current_user_id() -> str:
    return "demo-user"
```

With:

```python
def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    token_service: TokenService = Depends(get_token_service),
) -> str:
    payload = token_service.verify_access_token(credentials.credentials)
    return payload.subject
```

Map invalid or expired token to `401`.

- [ ] **Step 3: Add demo seed script**

Create:

```text
backend/scripts/seed_demo_user.py
```

Behavior:

```text
Create demo@example.com / password123 only if it does not already exist.
Use AuthService so the password is hashed exactly like production login.
```

- [ ] **Step 4: Run full backend tests**

Run:

```powershell
.\.venv\Scripts\python.exe -B -m pytest
```

Expected:

```text
all tests pass
```

---

## Phase 9: Provider Interfaces, Seed Implementations, And Redis Cache

**Purpose:** Make places, weather, transfer time, opening hours, and budget checks tool-backed and cacheable without requiring paid external APIs.

**Commit target:** `feat: add provider interfaces and redis cache`

### Task 9.1: Provider DTOs And Seed Providers

**Files:**

- Create: `backend/app/providers/base.py`
- Create: `backend/app/providers/seed.py`
- Create: `backend/app/services/providers.py`
- Create: `backend/app/schemas/providers.py`
- Test: `backend/tests/providers/test_seed_providers.py`

- [ ] **Step 1: Write failing tests for provider contracts**

Required contracts:

```python
class PlaceProvider:
    def search_places(self, *, query: str, city: str | None, limit: int = 5) -> list[PlaceResult]: ...

class WeatherProvider:
    def get_weather(self, *, city: str, date: str) -> WeatherResult: ...

class TransferTimeProvider:
    def estimate_transfer_time(self, *, origin_place_id: str, destination_place_id: str, mode: str) -> TransferTimeResult: ...

class OpeningHoursProvider:
    def check_opening_hours(self, *, place_id: str, date: str, start_time: str, end_time: str) -> OpeningHoursResult: ...
```

Run:

```powershell
.\.venv\Scripts\python.exe -B -m pytest backend\tests\providers\test_seed_providers.py
```

Expected:

```text
ImportError for missing providers module
```

- [ ] **Step 2: Implement deterministic seed providers**

Seed providers must return stable IDs:

```text
place:tokyo:sensoji
place:tokyo:ueno-park
place:tokyo:ramen-street
```

Weather and transfer results must be deterministic so conflict tests are stable.

### Task 9.2: Redis Cache Boundary

**Files:**

- Create: `backend/app/providers/cache.py`
- Modify: `backend/app/core/config.py`
- Test: `backend/tests/providers/test_provider_cache.py`

- [ ] **Step 1: Add tests for cache key semantics**

Required behavior:

```text
same provider request -> cache hit
different city/date/query -> cache miss
cache stores internal DTO dict, not raw third-party response
Redis outage -> provider still works without failing the business request
```

- [ ] **Step 2: Implement cache wrapper**

Use a boundary like:

```python
class CachedWeatherProvider:
    def __init__(self, provider: WeatherProvider, redis_client: Redis, ttl_seconds: int): ...
```

Do not let Redis become the source of truth.

### Task 9.3: ToolRegistry Provider Tools

**Files:**

- Modify: `backend/app/agent/tools.py`
- Modify: `backend/app/api/dependencies.py`
- Test: `backend/tests/agent/test_tool_registry_providers.py`

- [ ] **Step 1: Add failing tests for new tools**

Required tools:

```text
search_places
get_weather
estimate_transfer_time
check_opening_hours
calculate_budget
validate_itinerary
create_trip_candidate
```

Required safety:

```text
Every tool requires user_id, trip_id, agent_run_id.
Every tool writes ToolCall.
Provider tools return structured DTOs.
Unknown tool fails with ToolExecutionError.
```

- [ ] **Step 2: Implement tools through service/provider boundaries**

Do not let tools import SQLAlchemy models or repositories directly.

---

## Phase 10: Agent Runtime Adapter And Error Recovery

**Purpose:** Move Agent Runtime from scripted provider only to a real OpenAI-compatible adapter while keeping deterministic test paths.

**Commit target:** `feat: add openai-compatible agent provider`

### Task 10.1: Provider Adapter

**Files:**

- Create: `backend/app/agent/provider_openai_compatible.py`
- Modify: `backend/app/core/config.py`
- Test: `backend/tests/agent/test_provider_adapter.py`

- [ ] **Step 1: Add adapter tests**

Test with a fake HTTP transport, not a live model:

```text
UnifiedMessage -> OpenAI-compatible request messages
tool schema -> request tools
tool call response -> UnifiedToolCall
plain JSON response -> parsed dict
HTTP/model error -> ProviderError
```

- [ ] **Step 2: Implement adapter behind a Protocol**

Config fields:

```text
OPENAI_COMPATIBLE_BASE_URL
OPENAI_COMPATIBLE_API_KEY
OPENAI_COMPATIBLE_MODEL
OPENAI_COMPATIBLE_TIMEOUT_SECONDS
```

Default runtime should still use fake/seed provider in tests unless model config is explicitly present.

### Task 10.2: Runtime Retry And Structured Repair

**Files:**

- Create: `backend/app/agent/error_recovery.py`
- Modify: `backend/app/agent/runtime.py`
- Test: `backend/tests/agent/test_agent_error_recovery.py`

- [ ] **Step 1: Add tests for failure policy**

Required behavior:

```text
invalid structured output -> one repair/retry
persistent invalid output -> AgentRun.failed
tool error -> AgentRun.failed and ToolCall.error persisted
business validation blocking conflicts -> AgentRun.completed and Candidate.status=blocked
```

- [ ] **Step 2: Implement bounded retries**

No unbounded loops. Runtime config should include:

```text
max_model_attempts = 2
max_tool_attempts = 2
```

---

## Phase 11: Celery Agent Execution

**Purpose:** Move long-running Agent generation out of request/response while keeping publish synchronous and transactional.

**Commit target:** `feat: run agent generation through celery`

### Task 11.1: AgentRun Service And Generate API

**Files:**

- Create: `backend/app/services/agent_runs.py`
- Modify: `backend/app/api/v1/endpoints/trips.py`
- Modify: `backend/app/worker/tasks.py`
- Test: `backend/tests/services/test_agent_run_service.py`
- Test: `backend/tests/api/test_agent_generate_api.py`

- [ ] **Step 1: Add failing tests for async handoff**

Required API:

```text
POST /api/v1/trips/{trip_id}/generate -> 202 { agent_run_id }
POST /api/v1/trips/{trip_id}/adjust -> 202 { agent_run_id }
GET /api/v1/agent-runs/{run_id} -> status
```

Required behavior:

```text
API creates AgentRun.pending
Celery task transitions pending -> running -> completed/failed
Agent task creates TripCandidate only
Agent task never publishes
```

- [ ] **Step 2: Implement service and task**

Task signature:

```python
@celery_app.task(name="waypilot.run_agent")
def run_agent_task(agent_run_id: str) -> None:
    ...
```

For tests, call the service method directly or run Celery eagerly through config.

### Task 11.2: Cancel And Archive

**Files:**

- Modify: `backend/app/api/v1/endpoints/agent_runs.py`
- Modify: `backend/app/services/agent_runs.py`
- Modify: `backend/app/worker/tasks.py`
- Test: `backend/tests/api/test_agent_run_lifecycle.py`

- [ ] **Step 1: Add lifecycle tests**

Required behavior:

```text
POST /api/v1/agent-runs/{run_id}/cancel -> status cancelled when pending/running
completed run cannot be cancelled
archive task keeps AgentRun/ToolCall/Trace but may prune verbose events
```

---

## Phase 12: Vector RAG And Ingestion

**Purpose:** Replace keyword-only controlled retrieval with pgvector-backed retrieval while preserving user data isolation.

**Commit target:** `feat: add vector rag ingestion and retrieval`

### Task 12.1: Embedding Adapter And Ingest Pipeline

**Files:**

- Create: `backend/app/rag/embeddings.py`
- Create: `backend/app/rag/ingest.py`
- Create: `backend/scripts/seed_rag_documents.py`
- Modify: `backend/app/repositories/sqlalchemy.py`
- Test: `backend/tests/rag/test_rag_ingest.py`

- [ ] **Step 1: Add failing tests**

Required behavior:

```text
document content is chunked deterministically
embedding adapter writes 1536-dim vectors
re-ingesting same source updates existing document/chunks
private user document stores owner_user_id
```

- [ ] **Step 2: Implement deterministic fake embedding for tests**

Test embedding adapter:

```python
class DeterministicEmbeddingProvider:
    def embed(self, text: str) -> list[float]:
        ...
```

No live embedding API required in MVP.

### Task 12.2: Vector Retriever

**Files:**

- Create: `backend/app/rag/vector_retriever.py`
- Modify: `backend/app/api/dependencies.py`
- Test: `backend/tests/rag/test_vector_retriever.py`

- [ ] **Step 1: Add user isolation tests**

Required behavior:

```text
public documents are visible to all users
private documents are visible only to owner_user_id
city filter is respected
top-k limit is respected
RagHit includes document_id, chunk_id, source_type, title, city, score, snippet
```

---

## Phase 13: Frontend Product Loop

**Purpose:** Make the app usable through the browser, not only through OpenAPI.

**Commit target:** `feat: complete frontend planning loop`

### Task 13.1: Dev Proxy And Auth UI

**Files:**

- Modify: `frontend/vite.config.ts`
- Create: `frontend/src/auth/session.ts`
- Create: `frontend/src/pages/LoginPage.tsx`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add API client tests**

Required behavior:

```text
API client attaches Authorization Bearer token when present
401 clears session and sends user to /auth/login
Vite dev proxy forwards /api to http://localhost:8000
```

- [ ] **Step 2: Implement login and protected routes**

Do not store refresh tokens because refresh tokens are not part of MVP. Store access token in a small session module and keep the blast radius explicit.

### Task 13.2: Agent Console And Candidate Review

**Files:**

- Create: `frontend/src/pages/AgentConsolePage.tsx`
- Create: `frontend/src/components/ConflictList.tsx`
- Modify: `frontend/src/pages/TripDetailPage.tsx`
- Modify: `frontend/src/pages/CandidateReviewPage.tsx`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/types.ts`

- [ ] **Step 1: Add UI tests for the review loop**

Required browser flow:

```text
Trip detail -> Generate with Agent -> AgentRun polling -> Candidate link
Candidate page -> Validate -> conflict list
Warning conflicts require explicit checkbox before publish
Blocking conflicts disable publish
Publish returns version and updates trip detail
```

- [ ] **Step 2: Implement with TanStack Query**

Use server state for AgentRun/Candidate/Version. Use local React state only for UI choices such as warning conflict confirmations.

### Task 13.3: Version Timeline And Rollback Confirmation

**Files:**

- Create: `frontend/src/components/VersionTimeline.tsx`
- Modify: `frontend/src/pages/VersionsPage.tsx`

- [ ] **Step 1: Add version UI tests**

Required behavior:

```text
versions render in descending version_no
rollback requires confirmation
rollback result appears as a new version
old version rows remain visible
```

---

## Phase 14: Production Hardening And Documentation

**Purpose:** Make the project maintainable as an open-source-style application.

**Commit target:** `chore: harden local development and docs`

### Task 14.1: Error Responses And Logging

**Files:**

- Modify: `backend/app/main.py`
- Create: `backend/app/core/errors.py`
- Create: `backend/app/core/logging.py`
- Test: `backend/tests/api/test_error_responses.py`

- [ ] **Step 1: Add error response tests**

Required response shape:

```json
{
  "error": {
    "code": "trip_not_found",
    "message": "Trip not found",
    "request_id": "..."
  }
}
```

Do not leak stack traces or provider API keys.

### Task 14.2: Docker Full-Stack Verification

**Files:**

- Modify: `docker-compose.yml`
- Modify: `backend/Dockerfile`
- Modify: `frontend/Dockerfile` if missing
- Modify: `README.md`
- Test: manual smoke commands documented below

- [ ] **Step 1: Make Compose run full stack**

Required commands:

```powershell
docker compose up --build
```

Required reachable URLs:

```text
http://localhost:8000/docs
http://localhost:5173
```

### Task 14.3: CI And Docs Refresh

**Files:**

- Create: `.github/workflows/ci.yml`
- Modify: `README.md`
- Modify: `plan.md`
- Modify: `agent.md`

- [ ] **Step 1: Add CI workflow**

Required jobs:

```text
backend tests on Python 3.12
frontend typecheck/build on Node LTS
```

- [ ] **Step 2: Refresh docs**

Update docs to reflect:

```text
SQLAlchemy persistence is implemented for Trip, Candidate, Preference, AgentRun, ToolCall, RAG, AgentTrace.
Auth is now real JWT instead of demo-user after Phase 8.
Docker startup commands are current.
Remaining gaps are provider integrations, live model calls, production deployment, and optional real external APIs.
```

---

## Execution Order

Use this exact order:

```text
1. Phase 8 Auth And User Boundary
2. Phase 9 Provider Interfaces And Redis Cache
3. Phase 10 Agent Runtime Adapter And Error Recovery
4. Phase 11 Celery Agent Execution
5. Phase 12 Vector RAG And Ingestion
6. Phase 13 Frontend Product Loop
7. Phase 14 Production Hardening And Documentation
```

Reason:

```text
Auth must exist before private RAG, Agent tools, and frontend session logic are meaningful.
Provider tools must exist before model tool-calling is useful.
Celery is valuable after Agent runtime work has a durable AgentRun lifecycle.
Vector RAG should build on user isolation and provider/tool boundaries.
Frontend should consume stabilized APIs rather than chase backend shape changes.
Hardening/docs should close the loop after behavior stabilizes.
```

---

## Self-Review

Spec coverage:

```text
Auth/JWT/user isolation -> Phase 8
Provider interfaces and mock/seed implementations -> Phase 9
Redis cache boundary -> Phase 9
OpenAI-compatible Provider Adapter -> Phase 10
Runtime retries and structured output repair -> Phase 10
Celery async tasks -> Phase 11
pgvector RAG ingestion/retrieval -> Phase 12
Frontend login/Agent/review/version loop -> Phase 13
Logging/errors/OpenAPI/Docker/CI/docs -> Phase 14
```

Scope check:

```text
Each phase can be implemented and committed independently.
No phase requires real paid external map/weather/model APIs.
No phase allows Agent to publish or rollback.
No phase changes the Candidate/Version invariant.
```

Risk check:

```text
Highest-risk change is Phase 8 because it replaces demo-user and touches every protected API test.
Second-highest risk is Phase 11 because Celery changes runtime timing and lifecycle semantics.
Phase 13 should not start before Phase 8 and Phase 11 endpoints are stable.
```
