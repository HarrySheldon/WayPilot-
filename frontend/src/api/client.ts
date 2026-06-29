import type {
  AgentRun,
  AgentRunEvent,
  ToolCall,
  Trip,
  TripCandidate,
  TripCreateRequest,
  TripVersion,
  UserPreference,
} from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
    ...init,
  })

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
  }

  return response.json() as Promise<T>
}

export function listTrips(): Promise<Trip[]> {
  return request<Trip[]>('/trips')
}

export function getTrip(tripId: string): Promise<Trip> {
  return request<Trip>(`/trips/${tripId}`)
}

export function createTrip(data: TripCreateRequest): Promise<Trip> {
  return request<Trip>('/trips', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function getPreferences(): Promise<UserPreference> {
  return request<UserPreference>('/preferences')
}

export function listTripCandidates(tripId: string): Promise<TripCandidate[]> {
  return request<TripCandidate[]>(`/trips/${tripId}/candidates`)
}

export function getTripCandidate(candidateId: string): Promise<TripCandidate> {
  return request<TripCandidate>(`/trip-candidates/${candidateId}`)
}

export function validateTripCandidate(candidateId: string): Promise<TripCandidate> {
  return request<TripCandidate>(`/trip-candidates/${candidateId}/validate`, { method: 'POST' })
}

export function publishTripCandidate(candidateId: string, ignoredWarningConflictIds: string[]): Promise<TripVersion> {
  return request<TripVersion>(`/trip-candidates/${candidateId}/publish`, {
    method: 'POST',
    body: JSON.stringify({ ignored_warning_conflict_ids: ignoredWarningConflictIds }),
  })
}

export function discardTripCandidate(candidateId: string): Promise<TripCandidate> {
  return request<TripCandidate>(`/trip-candidates/${candidateId}/discard`, { method: 'POST' })
}

export function listTripVersions(tripId: string): Promise<TripVersion[]> {
  return request<TripVersion[]>(`/trips/${tripId}/versions`)
}

export function rollbackTripVersion(versionId: string): Promise<TripVersion> {
  return request<TripVersion>(`/trip-versions/${versionId}/rollback`, {
    method: 'POST',
    body: JSON.stringify({ publish_note: 'Rollback requested from the UI.' }),
  })
}

export function getAgentRun(runId: string): Promise<AgentRun> {
  return request<AgentRun>(`/agent-runs/${runId}`)
}

export function listAgentRunEvents(runId: string): Promise<AgentRunEvent[]> {
  return request<AgentRunEvent[]>(`/agent-runs/${runId}/events`)
}

export function listAgentRunToolCalls(runId: string): Promise<ToolCall[]> {
  return request<ToolCall[]>(`/agent-runs/${runId}/tool-calls`)
}
