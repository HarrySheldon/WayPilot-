import { describe, expect, test } from 'vitest'
import config from '../vite.config'

describe('vite config', () => {
  test('proxies api requests to the FastAPI backend in development', () => {
    const proxy = config.server?.proxy

    expect(proxy).toMatchObject({
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    })
  })
})
