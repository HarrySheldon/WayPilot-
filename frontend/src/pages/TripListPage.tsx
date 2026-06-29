import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Button, Space, Table, Tag, Typography } from 'antd'
import type { TableColumnsType } from 'antd'
import { listTrips } from '../api/client'
import type { Trip } from '../api/types'

const columns: TableColumnsType<Trip> = [
  {
    title: 'Title',
    dataIndex: 'title',
    render: (title, trip) => <Link to={`/trips/${trip.id}`}>{title}</Link>,
  },
  {
    title: 'Destination',
    dataIndex: 'destination',
  },
  {
    title: 'Dates',
    render: (_, trip) => [trip.start_date, trip.end_date].filter(Boolean).join(' to ') || 'Not set',
  },
  {
    title: 'Status',
    dataIndex: 'status',
    render: (status) => <Tag>{status}</Tag>,
  },
]

export function TripListPage() {
  const tripsQuery = useQuery({ queryKey: ['trips'], queryFn: listTrips })

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Space style={{ justifyContent: 'space-between', width: '100%' }}>
        <Typography.Title level={2} style={{ margin: 0 }}>
          Travel plans
        </Typography.Title>
        <Link to="/trips/new">
          <Button type="primary">New trip</Button>
        </Link>
      </Space>
      <Table<Trip>
        rowKey="id"
        columns={columns}
        dataSource={tripsQuery.data ?? []}
        loading={tripsQuery.isLoading}
        pagination={false}
      />
    </Space>
  )
}

