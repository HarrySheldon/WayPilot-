const TOKEN_KEY = 'waypilot.accessToken'

let memoryToken: string | null = null

export function getAccessToken(): string | null {
  const storage = getStorage()
  if (storage) {
    return storage.getItem(TOKEN_KEY)
  }
  return memoryToken
}

export function setAccessToken(token: string): void {
  const storage = getStorage()
  if (storage) {
    storage.setItem(TOKEN_KEY, token)
    return
  }
  memoryToken = token
}

export function clearSession(): void {
  const storage = getStorage()
  if (storage) {
    storage.removeItem(TOKEN_KEY)
  }
  memoryToken = null
}

export function notifyAuthenticated(): void {
  dispatchSessionEvent('waypilot:authenticated')
}

export function notifyUnauthorized(): void {
  dispatchSessionEvent('waypilot:unauthorized')
}

function getStorage(): Storage | null {
  try {
    return typeof window !== 'undefined' ? window.localStorage : null
  } catch {
    return null
  }
}

function dispatchSessionEvent(name: string): void {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event(name))
  }
}
