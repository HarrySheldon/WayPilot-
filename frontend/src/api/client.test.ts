import { beforeEach, describe, expect, test, vi } from 'vitest'
import { listTrips } from './client'
import { clearSession, getAccessToken, setAccessToken } from '../auth/session'

describe('api client', () => {
  beforeEach(() => {
    clearSession()
    vi.restoreAllMocks()
  })

  test('attaches authorization bearer token when present', async () => {
    setAccessToken('token-1')
    const fetchMock = vi.fn(async () => new Response(JSON.stringify([]), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    await listTrips()

    const calls = fetchMock.mock.calls as unknown as [string, RequestInit][]
    const init = calls[0][1]
    expect(init.headers).toMatchObject({
      Authorization: 'Bearer token-1',
    })
  })

  test('clears session when backend returns unauthorized', async () => {
    setAccessToken('token-1')
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ detail: 'Not authenticated' }), { status: 401 })))

    await expect(listTrips()).rejects.toThrow('Request failed: 401')

    expect(getAccessToken()).toBeNull()
  })
})
