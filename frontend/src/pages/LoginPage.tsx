import { useMutation } from '@tanstack/react-query'
import { Alert, Button, Card, Form, Input, Space, Typography } from 'antd'
import { useNavigate } from 'react-router-dom'
import { login } from '../api/client'
import type { LoginRequest } from '../api/types'
import { notifyAuthenticated, setAccessToken } from '../auth/session'

export function LoginPage() {
  const navigate = useNavigate()
  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: (token) => {
      setAccessToken(token.access_token)
      notifyAuthenticated()
      navigate('/trips', { replace: true })
    },
  })

  return (
    <Space direction="vertical" size={16} style={{ maxWidth: 420, width: '100%' }}>
      <Space direction="vertical" size={4}>
        <Typography.Title level={2} style={{ margin: 0 }}>
          WayPilot
        </Typography.Title>
        <Typography.Text type="secondary">Sign in to manage trips, candidates, and agent runs.</Typography.Text>
      </Space>
      <Card>
        <Form<LoginRequest>
          layout="vertical"
          initialValues={{ email: 'demo@example.com', password: 'password123' }}
          onFinish={(values) => loginMutation.mutate(values)}
        >
          <Form.Item name="email" label="Email" rules={[{ required: true }, { type: 'email' }]}>
            <Input autoComplete="email" />
          </Form.Item>
          <Form.Item name="password" label="Password" rules={[{ required: true }]}>
            <Input.Password autoComplete="current-password" />
          </Form.Item>
          {loginMutation.isError ? (
            <Alert type="error" showIcon message="Unable to sign in with those credentials." style={{ marginBottom: 16 }} />
          ) : null}
          <Button type="primary" htmlType="submit" loading={loginMutation.isPending} block>
            Sign in
          </Button>
        </Form>
      </Card>
    </Space>
  )
}
