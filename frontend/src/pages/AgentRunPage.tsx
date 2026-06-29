import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { Card, Descriptions, Empty, Space, Table, Tag, Timeline, Typography } from 'antd'
import type { TableColumnsType } from 'antd'
import { getAgentRun, listAgentRunToolCalls } from '../api/client'
import type { ToolCall } from '../api/types'

const toolColumns: TableColumnsType<ToolCall> = [
  { title: 'Tool', dataIndex: 'tool_name' },
  { title: 'Status', dataIndex: 'status', render: (status) => <Tag>{status}</Tag> },
  { title: 'Error', dataIndex: 'error', render: (error) => error ?? '-' },
]

export function AgentRunPage() {
  const { runId } = useParams()
  const runQuery = useQuery({
    queryKey: ['agent-run', runId],
    queryFn: () => getAgentRun(runId!),
    enabled: Boolean(runId),
  })
  const toolCallsQuery = useQuery({
    queryKey: ['agent-run-tool-calls', runId],
    queryFn: () => listAgentRunToolCalls(runId!),
    enabled: Boolean(runId),
  })

  if (!runQuery.data) {
    return runQuery.isLoading ? <Typography.Text>Loading agent run...</Typography.Text> : <Empty />
  }

  const run = runQuery.data

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Space>
        <Typography.Title level={2} style={{ margin: 0 }}>
          Agent run
        </Typography.Title>
        <Tag>{run.status}</Tag>
      </Space>
      <Card>
        <Descriptions column={2}>
          <Descriptions.Item label="Run">{run.id}</Descriptions.Item>
          <Descriptions.Item label="Trip">
            <Link to={`/trips/${run.trip_id}`}>{run.trip_id}</Link>
          </Descriptions.Item>
          <Descriptions.Item label="Candidate">{run.candidate_id ?? 'None'}</Descriptions.Item>
          <Descriptions.Item label="Error">{run.error_message ?? 'None'}</Descriptions.Item>
          <Descriptions.Item label="Request">{run.user_message}</Descriptions.Item>
        </Descriptions>
      </Card>
      <Card title="Events">
        <Timeline
          items={run.events.map((event) => ({
            key: event.id,
            children: (
              <Space direction="vertical" size={0}>
                <Typography.Text strong>{event.title}</Typography.Text>
                <Typography.Text type="secondary">{event.type}</Typography.Text>
              </Space>
            ),
          }))}
        />
      </Card>
      <Card title="Tool calls">
        <Table<ToolCall>
          rowKey="id"
          columns={toolColumns}
          dataSource={toolCallsQuery.data ?? []}
          loading={toolCallsQuery.isLoading}
          pagination={false}
        />
      </Card>
    </Space>
  )
}
