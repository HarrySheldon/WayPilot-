export function shouldPollAgentRun(status: string | undefined): boolean {
  return status === 'pending' || status === 'running' || status === 'tool_calling' || status === 'validating'
}
