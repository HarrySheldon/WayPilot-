import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { Empty, Space, Typography } from 'antd'
import { listTripVersions, rollbackTripVersion } from '../api/client'
import { VersionTimeline } from '../components/VersionTimeline'

export function VersionsPage() {
  const { tripId } = useParams()
  const queryClient = useQueryClient()
  const versionsQuery = useQuery({
    queryKey: ['trip-versions', tripId],
    queryFn: () => listTripVersions(tripId!),
    enabled: Boolean(tripId),
  })
  const rollbackMutation = useMutation({
    mutationFn: rollbackTripVersion,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['trip-versions', tripId] })
      await queryClient.invalidateQueries({ queryKey: ['trip', tripId] })
    },
  })

  if (!versionsQuery.data?.length && !versionsQuery.isLoading) {
    return <Empty description="No published versions yet." />
  }

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Space style={{ justifyContent: 'space-between', width: '100%' }}>
        <Typography.Title level={2} style={{ margin: 0 }}>
          Version history
        </Typography.Title>
        <Link to={`/trips/${tripId}`}>Back to trip</Link>
      </Space>
      <VersionTimeline
        versions={versionsQuery.data ?? []}
        rollingBackVersionId={rollbackMutation.variables ?? null}
        onRollback={(versionId) => rollbackMutation.mutate(versionId)}
      />
    </Space>
  )
}
