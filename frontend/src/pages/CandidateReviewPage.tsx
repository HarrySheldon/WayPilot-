import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { Button, Card, Empty, Space, Table, Tag, Typography } from 'antd'
import type { TableColumnsType } from 'antd'
import {
  discardTripCandidate,
  getTripCandidate,
  publishTripCandidate,
  validateTripCandidate,
} from '../api/client'
import type { Conflict } from '../api/types'

const conflictColumns: TableColumnsType<Conflict> = [
  {
    title: 'Severity',
    dataIndex: 'severity',
    render: (severity) => <Tag color={severity === 'blocking' ? 'red' : severity === 'warning' ? 'orange' : 'blue'}>{severity}</Tag>,
  },
  { title: 'Type', dataIndex: 'conflict_type' },
  { title: 'Message', dataIndex: 'message' },
]

export function CandidateReviewPage() {
  const { candidateId, tripId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const candidateQuery = useQuery({
    queryKey: ['trip-candidate', candidateId],
    queryFn: () => getTripCandidate(candidateId!),
    enabled: Boolean(candidateId),
  })
  const validateMutation = useMutation({
    mutationFn: () => validateTripCandidate(candidateId!),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['trip-candidate', candidateId] })
    },
  })
  const publishMutation = useMutation({
    mutationFn: () => {
      const warningIds = candidateQuery.data?.conflicts
        .filter((conflict) => conflict.severity === 'warning')
        .map((conflict) => conflict.id)
      return publishTripCandidate(candidateId!, warningIds ?? [])
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['trip', tripId] })
      navigate(`/trips/${tripId}`)
    },
  })
  const discardMutation = useMutation({
    mutationFn: () => discardTripCandidate(candidateId!),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['trip-candidate', candidateId] })
    },
  })

  if (!candidateQuery.data) {
    return candidateQuery.isLoading ? <Typography.Text>Loading candidate...</Typography.Text> : <Empty />
  }

  const candidate = candidateQuery.data
  const hasBlocking = candidate.conflicts.some((conflict) => conflict.severity === 'blocking')

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Space style={{ justifyContent: 'space-between', width: '100%' }}>
        <Space>
          <Typography.Title level={2} style={{ margin: 0 }}>
            Candidate review
          </Typography.Title>
          <Tag>{candidate.status}</Tag>
        </Space>
        <Space>
          <Button onClick={() => validateMutation.mutate()} loading={validateMutation.isPending}>
            Validate
          </Button>
          <Button danger onClick={() => discardMutation.mutate()} loading={discardMutation.isPending}>
            Discard
          </Button>
          <Button
            type="primary"
            disabled={hasBlocking || candidate.status === 'published'}
            onClick={() => publishMutation.mutate()}
            loading={publishMutation.isPending}
          >
            Publish
          </Button>
        </Space>
      </Space>
      <Card title="Conflicts">
        <Table<Conflict>
          rowKey="id"
          columns={conflictColumns}
          dataSource={candidate.conflicts}
          pagination={false}
          locale={{ emptyText: 'No conflicts detected.' }}
        />
      </Card>
      <Card title="Itinerary snapshot">
        <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(candidate.itinerary_snapshot, null, 2)}</pre>
      </Card>
    </Space>
  )
}
