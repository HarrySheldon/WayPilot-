import type { TripVersion } from '../api/types'

export function sortVersionsDescending(versions: TripVersion[]): TripVersion[] {
  return [...versions].sort((left, right) => right.version_no - left.version_no)
}
