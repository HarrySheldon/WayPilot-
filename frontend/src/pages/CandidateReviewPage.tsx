import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Button, Card, Checkbox, Empty, Space, Tag, Typography } from 'antd'
import {
  discardTripCandidate,
  getTripCandidate,
  publishTripCandidate,
  validateTripCandidate,
} from '../api/client'
import { ConflictList } from '../components/ConflictList'
import { canPublishCandidate } from './candidateReviewRules'

export function CandidateReviewPage() {
  const { candidateId, tripId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [confirmedWarningIds, setConfirmedWarningIds] = useState<Set<string>>(new Set())
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
      return publishTripCandidate(candidateId!, Array.from(confirmedWarningIds))
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
  const warningConflicts = candidate.conflicts.filter((conflict) => conflict.severity === 'warning')
  const canPublish = canPublishCandidate(candidate, confirmedWarningIds)
  const warningOptions = warningConflicts.map((conflict) => ({
    label: conflict.message,
    value: conflict.id,
  }))

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
            disabled={!canPublish}
            onClick={() => publishMutation.mutate()}
            loading={publishMutation.isPending}
          >
            Publish
          </Button>
        </Space>
      </Space>
      <Card title="Conflicts">
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <ConflictList conflicts={candidate.conflicts} />
          {warningOptions.length ? (
            <Checkbox.Group
              options={warningOptions}
              value={Array.from(confirmedWarningIds)}
              onChange={(values) => setConfirmedWarningIds(new Set(values.map(String)))}
            />
          ) : null}
        </Space>
      </Card>
      <Card title="Itinerary snapshot">
        <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(candidate.itinerary_snapshot, null, 2)}</pre>
      </Card>
    </Space>
  )
}
