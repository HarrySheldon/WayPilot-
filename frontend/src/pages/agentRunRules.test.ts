import { describe, expect, test } from 'vitest'
import { shouldPollAgentRun } from './agentRunRules'

describe('agent run rules', () => {
  test('polls active agent run statuses only', () => {
    expect(shouldPollAgentRun('pending')).toBe(true)
    expect(shouldPollAgentRun('running')).toBe(true)
    expect(shouldPollAgentRun('tool_calling')).toBe(true)
    expect(shouldPollAgentRun('validating')).toBe(true)
    expect(shouldPollAgentRun('completed')).toBe(false)
    expect(shouldPollAgentRun('failed')).toBe(false)
    expect(shouldPollAgentRun('cancelled')).toBe(false)
  })
})
