import { useMutation } from '@tanstack/react-query'
import { Button, Card, Form, Input, Space, Typography } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import { adjustTripWithAgent, generateTripWithAgent } from '../api/client'

interface AgentRequestForm {
  message: string
}

export function AgentConsolePage() {
  const { tripId } = useParams()
  const navigate = useNavigate()
  const generateMutation = useMutation({
    mutationFn: (message: string) => generateTripWithAgent(tripId!, message),
    onSuccess: (run) => navigate(`/agent-runs/${run.agent_run_id}`),
  })
  const adjustMutation = useMutation({
    mutationFn: (message: string) => adjustTripWithAgent(tripId!, message),
    onSuccess: (run) => navigate(`/agent-runs/${run.agent_run_id}`),
  })

  const submit = (mode: 'generate' | 'adjust') => (values: AgentRequestForm) => {
    if (mode === 'generate') {
      generateMutation.mutate(values.message)
      return
    }
    adjustMutation.mutate(values.message)
  }

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Space direction="vertical" size={4}>
        <Typography.Title level={2} style={{ margin: 0 }}>
          Agent console
        </Typography.Title>
        <Typography.Text type="secondary">Create a candidate itinerary or request a constrained adjustment.</Typography.Text>
      </Space>
      <Card title="Generate itinerary candidate">
        <Form<AgentRequestForm> layout="vertical" onFinish={submit('generate')}>
          <Form.Item name="message" label="Request" rules={[{ required: true }]}>
            <Input.TextArea rows={5} placeholder="Plan a 3-day Tokyo food and museum trip under 3000 USD." />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={generateMutation.isPending}>
            Generate with Agent
          </Button>
        </Form>
      </Card>
      <Card title="Adjust current plan">
        <Form<AgentRequestForm> layout="vertical" onFinish={submit('adjust')}>
          <Form.Item name="message" label="Adjustment" rules={[{ required: true }]}>
            <Input.TextArea rows={4} placeholder="Reduce the budget, avoid rain, or slow down the second day." />
          </Form.Item>
          <Button htmlType="submit" loading={adjustMutation.isPending}>
            Request adjustment
          </Button>
        </Form>
      </Card>
    </Space>
  )
}
