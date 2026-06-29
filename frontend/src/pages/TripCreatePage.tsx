import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Button, Form, Input, InputNumber, Select, Space, Typography } from 'antd'
import { useNavigate } from 'react-router-dom'
import { createTrip } from '../api/client'
import type { TripCreateRequest } from '../api/types'

export function TripCreatePage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const createTripMutation = useMutation({
    mutationFn: createTrip,
    onSuccess: async (trip) => {
      await queryClient.invalidateQueries({ queryKey: ['trips'] })
      navigate(`/trips/${trip.id}`)
    },
  })

  return (
    <Space direction="vertical" size={16} style={{ maxWidth: 760, width: '100%' }}>
      <Typography.Title level={2}>Create trip</Typography.Title>
      <Form<TripCreateRequest>
        layout="vertical"
        initialValues={{
          travelers_count: 1,
          pace: 'standard',
          interests: [],
          dietary_preferences: [],
          must_visit_places: [],
          avoidances: [],
          natural_language_note: '',
        }}
        onFinish={(values) => createTripMutation.mutate(values)}
      >
        <Form.Item name="title" label="Title" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.Item name="destination" label="Destination" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.Item name="travelers_count" label="Travelers" rules={[{ required: true }]}>
          <InputNumber min={1} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="budget_total" label="Budget">
          <InputNumber min={0} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="pace" label="Pace">
          <Select
            options={[
              { value: 'relaxed', label: 'Relaxed' },
              { value: 'standard', label: 'Standard' },
              { value: 'tight', label: 'Tight' },
            ]}
          />
        </Form.Item>
        <Form.Item name="interests" label="Interests">
          <Select mode="tags" />
        </Form.Item>
        <Form.Item name="dietary_preferences" label="Dietary preferences">
          <Select mode="tags" />
        </Form.Item>
        <Form.Item name="must_visit_places" label="Must-visit places">
          <Select mode="tags" />
        </Form.Item>
        <Form.Item name="avoidances" label="Avoidances">
          <Select mode="tags" />
        </Form.Item>
        <Form.Item name="natural_language_note" label="Additional notes">
          <Input.TextArea rows={4} />
        </Form.Item>
        <Button type="primary" htmlType="submit" loading={createTripMutation.isPending}>
          Save plan
        </Button>
      </Form>
    </Space>
  )
}

