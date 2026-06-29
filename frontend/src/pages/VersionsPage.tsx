import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { Button, Empty, Space, Table, Tag, Typography } from 'antd'
import type { TableColumnsType } from 'antd'
import { listTripVersions, rollbackTripVersion } from '../api/client'
import type { TripVersion } from '../api/types'

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
  const columns: TableColumnsType<TripVersion> = [
    { title: 'Version', dataIndex: 'version_no', render: (versionNo) => <Tag>v{versionNo}</Tag> },
    { title: 'Source', dataIndex: 'source_type' },
    { title: 'Candidate', dataIndex: 'source_candidate_id' },
    { title: 'Warnings ignored', render: (_, version) => version.ignored_warning_conflict_ids.length },
    {
      title: 'Action',
      render: (_, version) => (
        <Button size="small" onClick={() => rollbackMutation.mutate(version.id)} loading={rollbackMutation.isPending}>
          Rollback
        </Button>
      ),
    },
  ]

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
      <Table<TripVersion>
        rowKey="id"
        columns={columns}
        dataSource={versionsQuery.data ?? []}
        loading={versionsQuery.isLoading}
        pagination={false}
      />
    </Space>
  )
}
