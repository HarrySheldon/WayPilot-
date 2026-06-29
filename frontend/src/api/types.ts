export interface TripPreference {
  destination: string
  pace: string
  interests: string[]
  dietary_preferences: string[]
  must_visit_places: string[]
  avoidances: string[]
  natural_language_note: string
}

export interface Trip {
  id: string
  user_id: string
  title: string
  destination: string
  start_date: string | null
  end_date: string | null
  travelers_count: number
  budget_total: number | null
  status: string
  active_version_id: string | null
  preference: TripPreference | null
}

export interface TripCreateRequest {
  title: string
  destination: string
  start_date?: string | null
  end_date?: string | null
  travelers_count: number
  budget_total?: number | null
  pace: string
  interests: string[]
  dietary_preferences: string[]
  must_visit_places: string[]
  avoidances: string[]
  natural_language_note: string
}

export interface UserPreference {
  user_id: string
  default_pace: string
  interests: string[]
  dietary_preferences: string[]
  avoidances: string[]
}

export interface Conflict {
  id: string
  severity: 'blocking' | 'warning' | 'info' | string
  conflict_type: string
  message: string
}

export interface TripCandidate {
  id: string
  trip_id: string
  source_type: string
  source_agent_run_id: string | null
  base_version_id: string | null
  status: string
  itinerary_snapshot: Record<string, unknown>
  budget_snapshot: Record<string, unknown>
  preference_snapshot: Record<string, unknown>
  validation_summary: Record<string, number>
  conflicts: Conflict[]
}

export interface TripVersion {
  id: string
  trip_id: string
  version_no: number
  source_candidate_id: string
  source_type: string
  source_agent_run_id: string | null
  rolled_back_from_version_id: string | null
  itinerary_snapshot: Record<string, unknown>
  budget_snapshot: Record<string, unknown>
  preference_snapshot: Record<string, unknown>
  conflict_snapshot: Conflict[]
  ignored_warning_conflict_ids: string[]
  publish_note: string | null
}

export interface AgentRunEvent {
  id: string
  agent_run_id: string
  type: string
  title: string
  detail: string
  payload: Record<string, unknown>
}

export interface AgentRun {
  id: string
  user_id: string
  trip_id: string
  user_message: string
  status: string
  candidate_id: string | null
  error_message: string | null
  events: AgentRunEvent[]
}

export interface ToolCall {
  id: string
  agent_run_id: string
  tool_name: string
  arguments: Record<string, unknown>
  status: string
  result: Record<string, unknown>
  error: string | null
}
