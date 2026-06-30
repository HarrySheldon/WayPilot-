import { Button, Popconfirm, Space, Tag, Timeline, Typography } from 'antd'
import type { TripVersion } from '../api/types'
import { sortVersionsDescending } from './versionTimelineRules'

interface VersionTimelineProps {
  versions: TripVersion[]
  rollingBackVersionId: string | null
  onRollback: (versionId: string) => void
}

export function VersionTimeline({ versions, rollingBackVersionId, onRollback }: VersionTimelineProps) {
  return (
    <Timeline
      items={sortVersionsDescending(versions).map((version) => ({
        key: version.id,
        children: (
          <Space direction="vertical" size={4} style={{ width: '100%' }}>
            <Space wrap>
              <Tag color="blue">v{version.version_no}</Tag>
              <Typography.Text strong>{version.source_type}</Typography.Text>
              <Typography.Text type="secondary">{version.source_candidate_id}</Typography.Text>
              {version.rolled_back_from_version_id ? <Tag>rollback</Tag> : null}
            </Space>
            <Typography.Text type="secondary">{version.publish_note ?? 'No publish note'}</Typography.Text>
            <Popconfirm
              title={`Rollback to v${version.version_no}?`}
              description="Rollback creates a new version and keeps this historical version unchanged."
              okText="Rollback"
              cancelText="Cancel"
              onConfirm={() => onRollback(version.id)}
            >
              <Button size="small" loading={rollingBackVersionId === version.id}>
                Rollback
              </Button>
            </Popconfirm>
          </Space>
        ),
      }))}
    />
  )
}
