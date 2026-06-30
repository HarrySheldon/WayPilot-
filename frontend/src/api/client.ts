import type {
  AgentRun,
  AgentRunAccepted,
  AgentRunEvent,
  AuthToken,
  CurrentUser,
  LoginRequest,
  ToolCall,
  Trip,
  TripCandidate,
  TripCreateRequest,
  TripVersion,
  UserPreference,
} from './types'
import { clearSession, getAccessToken, notifyUnauthorized } from '../auth/session'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = buildHeaders(init?.headers)
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...headers,
    },
  })

  if (!response.ok) {
    if (response.status === 401) {
      clearSession()
      notifyUnauthorized()
    }
    throw new Error(`Request failed: ${response.status}`)
  }

  return response.json() as Promise<T>
}

function buildHeaders(headers?: HeadersInit): Record<string, string> {
  const merged: Record<string, string> = { 'Content-Type': 'application/json' }
  new Headers(headers).forEach((value, key) => {
    merged[key] = value
  })
  const token = getAccessToken()
  if (token) {
    merged.Authorization = `Bearer ${token}`
  }
  return merged
}

export function login(data: LoginRequest): Promise<AuthToken> {
  return request<AuthToken>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function getCurrentUser(): Promise<CurrentUser> {
  return request<CurrentUser>('/users/me')
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

export function generateTripWithAgent(tripId: string, message: string): Promise<AgentRunAccepted> {
  return request<AgentRunAccepted>(`/trips/${tripId}/generate`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  })
}

export function adjustTripWithAgent(tripId: string, message: string): Promise<AgentRunAccepted> {
  return request<AgentRunAccepted>(`/trips/${tripId}/adjust`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  })
}

export function listAgentRunEvents(runId: string): Promise<AgentRunEvent[]> {
  return request<AgentRunEvent[]>(`/agent-runs/${runId}/events`)
}

export function listAgentRunToolCalls(runId: string): Promise<ToolCall[]> {
  return request<ToolCall[]>(`/agent-runs/${runId}/tool-calls`)
}
