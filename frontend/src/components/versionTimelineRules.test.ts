import { describe, expect, test } from 'vitest'
import { sortVersionsDescending } from './versionTimelineRules'
import type { TripVersion } from '../api/types'

function version(versionNo: number): TripVersion {
  return {
    id: `version-${versionNo}`,
    trip_id: 'trip-1',
    version_no: versionNo,
    source_candidate_id: `candidate-${versionNo}`,
    source_type: 'agent',
    source_agent_run_id: null,
    rolled_back_from_version_id: null,
    itinerary_snapshot: {},
    budget_snapshot: {},
    preference_snapshot: {},
    conflict_snapshot: [],
    ignored_warning_conflict_ids: [],
    publish_note: null,
  }
}

describe('version timeline rules', () => {
  test('sorts versions in descending version number without mutating input', () => {
    const input = [version(1), version(3), version(2)]

    const sorted = sortVersionsDescending(input)

    expect(sorted.map((item) => item.version_no)).toEqual([3, 2, 1])
    expect(input.map((item) => item.version_no)).toEqual([1, 3, 2])
  })
})
