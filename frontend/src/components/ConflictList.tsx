import { Table, Tag } from 'antd'
import type { TableColumnsType } from 'antd'
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

export function ConflictList({ conflicts }: { conflicts: Conflict[] }) {
  return (
    <Table<Conflict>
      rowKey="id"
      columns={conflictColumns}
      dataSource={conflicts}
      pagination={false}
      locale={{ emptyText: 'No conflicts detected.' }}
    />
  )
}
