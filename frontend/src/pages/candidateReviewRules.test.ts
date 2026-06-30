import { describe, expect, test } from 'vitest'
import { canPublishCandidate } from './candidateReviewRules'
import type { TripCandidate } from '../api/types'

const baseCandidate: TripCandidate = {
  id: 'candidate-1',
  trip_id: 'trip-1',
  source_type: 'agent',
  source_agent_run_id: 'run-1',
  base_version_id: null,
  status: 'ready',
  itinerary_snapshot: {},
  budget_snapshot: {},
  preference_snapshot: {},
  validation_summary: {},
  conflicts: [],
}

describe('candidate review rules', () => {
  test('blocks publish when candidate has blocking conflicts', () => {
    const candidate = {
      ...baseCandidate,
      conflicts: [{ id: 'block-1', severity: 'blocking', conflict_type: 'time', message: 'Too tight' }],
    }

    expect(canPublishCandidate(candidate, new Set())).toBe(false)
  })

  test('requires every warning conflict to be explicitly confirmed', () => {
    const candidate = {
      ...baseCandidate,
      conflicts: [
        { id: 'warn-1', severity: 'warning', conflict_type: 'weather', message: 'Rain' },
        { id: 'warn-2', severity: 'warning', conflict_type: 'budget', message: 'Over budget' },
      ],
    }

    expect(canPublishCandidate(candidate, new Set(['warn-1']))).toBe(false)
    expect(canPublishCandidate(candidate, new Set(['warn-1', 'warn-2']))).toBe(true)
  })
})
