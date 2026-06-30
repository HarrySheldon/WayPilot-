import type { TripCandidate } from '../api/types'

export function canPublishCandidate(candidate: TripCandidate, confirmedWarningIds: Set<string>): boolean {
  if (candidate.status === 'published') {
    return false
  }
  if (candidate.conflicts.some((conflict) => conflict.severity === 'blocking')) {
    return false
  }
  return candidate.conflicts
    .filter((conflict) => conflict.severity === 'warning')
    .every((conflict) => confirmedWarningIds.has(conflict.id))
}
