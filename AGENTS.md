# WayPilot Agent Instructions

## Project Context

WayPilot is a personalized travel planning and dynamic adjustment platform.

Use these design documents as the source of truth before implementing or changing behavior:

- `plan.md`: overall project plan, frontend/backend architecture, domain model, Candidate/Version workflow, MVP phases, and test strategy.
- `agent.md`: WayPilot Agent subsystem design, including Agent Runtime, tools, RAG, structured output, trace, retries, and safety boundaries.

## Core Product Boundaries

- WayPilot is not a generic travel guide site.
- WayPilot is not a simple itinerary note-taking app.
- WayPilot is a travel planning platform with itinerary management, versioning, conflict detection, and Agent tool interfaces.
- WayPilot Agent is not a generic chatbot.
- WayPilot Agent is a lightweight Agent Runtime for travel planning that produces auditable candidate itineraries.

## Architecture Rules

- Use a modular monolith for the first version.
- Backend code follows API / Service / Repository / Model layering.
- Business rules, permissions, transactions, conflict detection, publishing, and rollback logic belong in the Service layer.
- Repository code handles data access only.
- API handlers should stay thin.
- Agent tools must call the Service layer through Tool Registry.
- Agent code must not call repositories or database models directly.
- Frontend code should use TanStack Query for server state and local React state for UI-only state.

## Candidate And Version Rules

- Agent output must become a `TripCandidate`; it must not directly overwrite the official itinerary.
- User itinerary edits that affect schedule, places, budget, preferences, or constraints must also create a `TripCandidate`.
- `TripCandidate.validate` is a dry-run validation step.
- `TripCandidate.publish` is the only path to create a new `TripVersion`.
- Publishing must run in one database transaction.
- Publishing must re-run deterministic validation on the backend.
- Blocking conflicts prevent publishing.
- Warning conflicts require explicit user confirmation before publishing.
- `TripVersion` is immutable.
- Rollback creates a new `TripVersion`; it must not mutate or delete historical versions.
- Current official itinerary data is stored in structured projection tables.
- Candidate and historical version data are stored as full snapshots.

## Agent Safety Rules

- The Agent may create candidates.
- The Agent may not publish candidates.
- The Agent may not rollback versions.
- The Agent may not bypass deterministic validation.
- The Agent may not access another user's trips, preferences, RAG documents, or traces.
- Tool calls must include `user_id`, `trip_id`, and `agent_run_id` context where applicable.
- Tool calls must be recorded as `ToolCall` records.
- Agent execution must be traceable through `AgentRun`, `AgentRunEvent`, and `AgentTrace`.

## External Data Rules

- First-version external data access uses Provider interfaces plus mock or seed implementations.
- Do not make real map, weather, traffic, or opening-hours APIs mandatory in the MVP.
- Provider responses must be converted to internal DTOs before reaching business logic.
- Redis may cache provider results and Agent temporary state.
- Redis is not the source of truth for business data.

## RAG Rules

- First-version RAG uses controlled knowledge sources only.
- Do not implement internet crawling in the MVP.
- Public knowledge may be shared across users.
- User preference and historical trip RAG data must be user-scoped.
- RAG provides context, not deterministic facts.
- Weather, opening hours, transfer time, and budget checks must use tools or backend services.

## Structured Output Rules

- Agent itinerary output must be strict JSON.
- Do not mix natural language prose into structured itinerary output.
- Validate Agent output with Pydantic before creating a `TripCandidate`.
- `place_id` values must come from place-search tool results.
- `rag_citations` must refer to RAG hits from the current run.
- Invalid structured output may be repaired or retried once; persistent invalid output fails the `AgentRun`.

## Testing Expectations

Prioritize tests for:

- Candidate publish transaction behavior.
- Blocking conflicts preventing publish.
- Warning conflicts requiring explicit confirmation.
- Publishing creating a new immutable `TripVersion`.
- Rollback creating a new version instead of mutating history.
- Agent output creating candidates only.
- Tool Registry enforcing user and trip permissions.
- Invalid structured output causing `AgentRun.failed`.

## Implementation Guidance

- Keep changes scoped to the confirmed design in `plan.md` and `agent.md`.
- Prefer small, testable modules over large files.
- Add abstractions only when they protect a real boundary already described in the design docs.
- When implementing a complex feature, check established open-source or official best practices first; if no suitable practice exists, implement the smallest reliable version.
- Do not add unrelated product features while implementing the MVP.
- If a requested change conflicts with these instructions, ask for clarification before changing core boundaries.
