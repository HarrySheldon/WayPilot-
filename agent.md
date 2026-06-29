# WayPilot Agent 设计文档

## 1. 定位

WayPilot Agent 是嵌入 WayPilot 平台的旅行规划智能体。它不是普通聊天机器人，也不是普通 RAG 问答系统，而是面向旅行规划场景的自研轻量级 Agent Runtime。

Agent 的职责是：

- 理解用户自然语言需求。
- 抽取目的地、时间、预算、同行人、兴趣、饮食、节奏、必去地点、避雷项等旅行约束。
- 检索城市攻略、景点说明、餐厅介绍、用户历史偏好和历史行程。
- 调用标准业务工具查询地点、天气、交通、预算、开放时间。
- 输出严格结构化 JSON 行程。
- 创建 `TripCandidate`。
- 记录 `AgentRun`、`AgentRunEvent`、`ToolCall` 和 `AgentTrace`。

Agent 不负责：

- 发布正式行程。
- 回滚版本。
- 绕过后端 Service 直接写数据库。
- 替代后端确定性冲突检测。
- 直接访问其他用户数据。

## 2. Runtime 边界

Agent Runtime 负责统一管理：

- 消息历史。
- 模型调用。
- RAG 检索。
- 工具调用。
- Structured Output。
- 错误恢复。
- Trace 记录。

第一版执行流程：

```text
1. build_context
2. extract_constraints
3. retrieve_rag
4. call_required_tools
5. generate_structured_itinerary
6. validate_output_schema
7. create_trip_candidate
8. run_deterministic_validation
9. write_trace
```

这些是 Runtime 执行阶段，不表示将 Agent Runtime 定义为简单状态机。

运行约束：

- 不做无限自主循环。
- 不允许 Agent 发布正式版本。
- 不允许 Agent 回滚版本。
- 工具调用次数设置上限。
- 模型调用次数设置上限。
- 失败后进入 `failed`，并记录原因。

## 3. Runtime 组件

```text
AgentRuntime
  编排一次 AgentRun 的生命周期。

MessageStore
  管理统一消息历史。

ProviderAdapter
  适配 OpenAI-compatible 模型服务。

RagRetriever
  检索 pgvector 上下文。

ToolRegistry
  注册和执行工具。

StructuredOutputValidator
  校验模型输出 JSON Schema。

TraceRecorder
  记录约束、RAG、ToolCall、输出、冲突。

ErrorRecoveryPolicy
  处理模型输出非法、工具失败、超时、重试。
```

## 4. AgentRun

`AgentRun.status`：

```text
pending
running
tool_calling
validating
completed
failed
cancelled
```

第一版运行反馈采用：

```text
轮询 AgentRun 状态 + 展示关键步骤日志
```

不做复杂实时 token 流式输出。

## 5. AgentRunEvent

事件模型：

```text
AgentRunEvent:
  id
  agent_run_id
  type
  title
  detail
  payload
  created_at
```

事件类型：

```text
intent_extracted
rag_retrieved
tool_called
tool_completed
draft_generated
validation_started
conflict_detected
candidate_created
run_failed
run_cancelled
```

前端轮询接口：

```text
GET /api/v1/agent-runs/{run_id}
GET /api/v1/agent-runs/{run_id}/events
```

## 6. Unified Message Schema

内部统一消息结构：

```text
UnifiedMessage:
  role: system | user | assistant | tool
  content
  tool_calls
  tool_call_id
  metadata
  created_at
```

工具调用结构：

```text
UnifiedToolCall:
  id
  name
  arguments
```

工具结果结构：

```text
UnifiedToolResult:
  tool_call_id
  name
  status: success | error
  result
  error
```

Provider Adapter 职责：

```text
内部 UnifiedMessage -> OpenAI-compatible request
OpenAI-compatible response -> UnifiedMessage / UnifiedToolCall
```

第一版支持：

```text
OpenAI-compatible Chat Completions
Provider: openai / deepseek / qwen-compatible
```

第一版不接：

```text
Responses API
Assistants API
复杂多模态
```

## 7. Tool Registry

第一版工具：

```text
search_places
get_weather
estimate_transfer_time
calculate_budget
validate_itinerary
create_trip_candidate
```

不暴露给 Agent 的工具：

```text
publish_trip_candidate
rollback_trip_version
```

规则：

- Tool 必须携带 `user_id` / `trip_id` / `agent_run_id` 上下文。
- Tool 内部复用 Service 权限校验。
- Tool 参数和结果使用 Pydantic Schema。
- ToolCall 必须落库。
- Tool 失败必须返回结构化错误。
- Agent 不能通过工具绕过发布确认。

## 8. RAG

第一版 RAG 范围：

```text
受控知识库 + 用户历史偏好 + 已确认行程摘要
不做互联网实时爬取
```

数据类型：

```text
city_guide          城市攻略
place_intro         景点说明
restaurant_intro    餐厅介绍
user_preference     用户历史偏好摘要
trip_summary        已确认历史行程摘要
```

存储：

```text
PostgreSQL + pgvector
```

核心表：

```text
RagDocument:
  id
  owner_user_id nullable
  source_type
  source_id
  title
  city
  locale
  content
  metadata
  created_at

RagChunk:
  id
  document_id
  chunk_index
  content
  embedding
  metadata
  created_at
```

检索返回：

```text
RagHit:
  document_id
  chunk_id
  source_type
  source_id
  title
  city
  score
  snippet
```

规则：

- 公共攻略可所有用户检索。
- 用户偏好和历史行程只允许当前用户检索。
- RAG 只提供上下文，不作为确定性事实来源。
- 天气、开放时间、交通、预算必须走工具。
- Agent 输出中应记录使用过的 RAG hit，进入 `AgentTrace`。

## 9. Structured Output

Agent 输出必须是严格 JSON，不允许混合自然语言正文。

第一版结构：

```text
StructuredItineraryOutput:
  trip_summary
  timezone
  currency
  assumptions
  days[]
  budget_summary
  rag_citations[]
```

`days[]`：

```text
date
city
items[]
```

`items[]`：

```text
temp_id
title
item_type: attraction | restaurant | transport | hotel | free_time | note
place_id nullable
place_name
start_time
end_time
estimated_cost
transport_to_next
notes
preference_tags
```

规则：

- `start_time` / `end_time` 使用目的地本地时间。
- `place_id` 只能来自 `search_places` 工具结果，Agent 不能自己编。
- `estimated_cost` 是估算值，后端预算服务会重新计算。
- `transport_to_next` 是建议，后端交通估算服务会重新校验。
- `rag_citations` 只能引用本次 RAG 返回的 `chunk_id`。
- 冲突不由 Agent 最终决定，后端重新检测。
- 输出不合法时 Runtime 最多重试一次，仍失败则 `AgentRun.failed`。

后端处理规则：

```text
1. Pydantic 校验 JSON Schema
2. 校验 place_id 是否来自工具结果
3. 校验 rag_citations 是否来自本次 RAG hit
4. 规范化时间、金额、枚举
5. 转为 TripCandidate snapshot
6. 执行确定性冲突检测
```

## 10. Agent Trace

AgentTrace 记录：

```text
用户意图
结构化约束
RAG 检索结果
工具调用参数
工具返回摘要
Structured Output 校验结果
冲突检测结果
Candidate 创建结果
版本变化
```

Trace 目标：

- 支持问题追踪。
- 支持执行复盘。
- 支持 Agent 调优。
- 支持安全审计。

日志脱敏：

- 不记录明文 token。
- 不记录 API key。
- Provider 原始请求默认不完整落库。
- 可记录 prompt 摘要、约束摘要、工具参数、工具结果摘要。

## 11. 错误处理与重试

AgentRun 重试策略：

```text
整体最多重试 1 次
单个工具最多重试 2 次
Structured Output 修复/重试最多 1 次
Celery task 配置 soft timeout / hard timeout
所有重试写入 AgentRunEvent
```

失败分类：

```text
model_error
tool_error
schema_validation_error
business_validation_blocked
timeout
cancelled
unexpected_error
```

语义：

```text
business_validation_blocked:
  不是系统失败。
  表示 Candidate 创建成功，但存在 blocking conflict。
  AgentRun 可以是 completed，Candidate.status = blocked。

model_error / tool_error / schema_validation_error / timeout:
  AgentRun.status = failed。
  不创建可发布 Candidate，或 Candidate.status = discarded / invalid。

cancelled:
  AgentRun.status = cancelled。
  不算 failed。
```

## 12. Agent 安全边界

Agent 安全规则：

- Agent Tool 必须携带 `user_id` / `trip_id` / `agent_run_id`。
- Tool 内部复用 Service 权限校验。
- Agent 不能发布 Candidate。
- Agent 不能回滚 Version。
- Agent 不能直接读取其他用户 RAG。
- Agent 不能直接访问 Repository / Model。
- Agent 不能绕过 TripCandidate 直接修改正式行程。

## 13. 与平台的关系

Agent 与平台之间的边界：

```text
Agent Runtime
 -> Tool Registry
 -> Service Layer
 -> Repository Layer
 -> PostgreSQL / Redis / Provider
```

Agent 的输出进入：

```text
TripCandidate
```

平台发布后进入：

```text
TripVersion
TripDay / ItineraryItem / BudgetItem 当前投影
```

因此 Agent 是候选方案生成器，不是正式业务状态的最终写入者。
