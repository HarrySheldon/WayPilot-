import { useQuery } from '@tanstack/react-query'
import { Card, Descriptions, Empty, Typography } from 'antd'
import { getPreferences } from '../api/client'

export function PreferencesPage() {
  const preferencesQuery = useQuery({ queryKey: ['preferences'], queryFn: getPreferences, retry: false })

  if (!preferencesQuery.data) {
    return (
      <Empty
        description={
          preferencesQuery.isLoading ? 'Loading preferences...' : 'No preferences saved for the demo user.'
        }
      />
    )
  }

  const preferences = preferencesQuery.data

  return (
    <Card>
      <Typography.Title level={2}>Global preferences</Typography.Title>
      <Descriptions column={1}>
        <Descriptions.Item label="Default pace">{preferences.default_pace}</Descriptions.Item>
        <Descriptions.Item label="Interests">{preferences.interests.join(', ') || 'None'}</Descriptions.Item>
        <Descriptions.Item label="Dietary preferences">
          {preferences.dietary_preferences.join(', ') || 'None'}
        </Descriptions.Item>
        <Descriptions.Item label="Avoidances">{preferences.avoidances.join(', ') || 'None'}</Descriptions.Item>
      </Descriptions>
    </Card>
  )
}
