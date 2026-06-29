import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { Button, Card, Descriptions, Empty, Space, Tag, Typography } from 'antd'
import { getTrip } from '../api/client'

export function TripDetailPage() {
  const { tripId } = useParams()
  const tripQuery = useQuery({
    queryKey: ['trip', tripId],
    queryFn: () => getTrip(tripId!),
    enabled: Boolean(tripId),
  })

  if (!tripQuery.data) {
    return tripQuery.isLoading ? <Typography.Text>Loading trip...</Typography.Text> : <Empty />
  }

  const trip = tripQuery.data

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Space>
        <Typography.Title level={2} style={{ margin: 0 }}>
          {trip.title}
        </Typography.Title>
        <Tag>{trip.status}</Tag>
        <Link to={`/trips/${trip.id}/versions`}>
          <Button>Versions</Button>
        </Link>
      </Space>
      <Card>
        <Descriptions column={2}>
          <Descriptions.Item label="Destination">{trip.destination}</Descriptions.Item>
          <Descriptions.Item label="Travelers">{trip.travelers_count}</Descriptions.Item>
          <Descriptions.Item label="Budget">{trip.budget_total ?? 'Not set'}</Descriptions.Item>
          <Descriptions.Item label="Active version">{trip.active_version_id ?? 'None'}</Descriptions.Item>
          <Descriptions.Item label="Pace">{trip.preference?.pace ?? 'standard'}</Descriptions.Item>
          <Descriptions.Item label="Interests">
            {trip.preference?.interests.length ? trip.preference.interests.join(', ') : 'None'}
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </Space>
  )
}
