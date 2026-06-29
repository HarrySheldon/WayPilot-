# WayPilot 项目计划文档

## 1. 项目目标

WayPilot 是一个个性化旅行规划与动态调整平台，目标是把旅行计划从“聊天生成文本”升级为“可校验、可发布、可回滚、可审计”的业务系统。

系统由两部分组成：

- WayPilot 平台：负责用户、偏好、旅行计划、候选草案、正式版本、冲突检测、预算、API、前端展示和异步任务。
- WayPilot Agent：负责理解自然语言需求、检索上下文、调用工具、生成结构化候选行程，并记录执行过程。

第一版采用模块化单体架构，不拆微服务。后端、Agent Runtime、Tool Registry、RAG、Provider 都放在同一后端代码库内，通过清晰的模块边界隔离职责。

## 2. 非目标

第一版不实现：

- 互联网实时爬取。
- 真实地图、天气、交通 API 强依赖。
- token 级实时流式输出。
- 多租户后台。
- 复杂 RBAC。
- 多 Agent 协作。
- MCP Client 实际接入。
- Agent 自动发布正式行程。
- Agent 自动回滚版本。
- 微服务拆分。

## 3. 技术栈

后端：Python、FastAPI、Pydantic、SQLAlchemy、Alembic、PostgreSQL、Redis、Celery、Pytest。

前端：React、TypeScript、Vite、Ant Design、TanStack Query。

Agent：自研轻量级 Agent Runtime、OpenAI-compatible Provider Adapter、Unified Message Schema、Tool Calling、RAG、Structured Output、Agent Trace、PostgreSQL + pgvector。

工程化：Docker Compose、OpenAPI、Git、日志与异常处理、分层架构。

## 4. 总体架构

```text
frontend/
  React + TypeScript + Vite + Ant Design + TanStack Query

backend/
  FastAPI API Layer
  Service Layer
  Repository Layer
  SQLAlchemy Models
  Agent Runtime
  Tool Registry
  RAG
  Provider Interfaces

worker/
  Celery tasks

infra/
  Docker Compose
  PostgreSQL
  Redis
  pgvector
```

业务调用路径：

```text
Frontend -> FastAPI API -> Service Layer -> Repository Layer -> PostgreSQL
```

Agent 调用路径：

```text
Agent Runtime -> Tool Registry -> Service Layer -> Repository Layer -> PostgreSQL / Redis / Provider
```

## 5. 核心业务闭环

主链路：

```text
创建旅行计划
 -> 生成初版行程
 -> AgentRun
 -> TripCandidate
 -> 冲突检测
 -> 用户审核候选草案
 -> 发布为 TripVersion
 -> 重建当前结构化行程投影
```

动态调整链路：

```text
当前正式 TripVersion
 -> 用户提出调整需求
 -> AgentRun
 -> TripCandidate(source_type = partial_adjustment)
 -> 冲突检测
 -> 用户审核
 -> 发布为新的 TripVersion
```

手动编辑链路：

```text
当前正式 TripVersion
 -> 用户编辑行程主体
 -> TripCandidate(source_type = user_edit)
 -> 冲突检测
 -> 用户审核
 -> 发布为新的 TripVersion
```

## 6. 核心设计原则

- Agent 只生成候选草案，不直接修改正式行程。
- 业务规则由后端 Service 确定性校验，不交给模型最终判断。
- Candidate 发布必须经过用户确认。
- 发布 Candidate 必须在单个数据库事务内完成。
- 历史版本不可变。
- 回滚创建新版本，不覆盖旧版本。
- 当前正式行程使用结构化表，候选草案和历史版本使用 JSON 快照。
- 前端只调用公开业务 API。
- Agent 只能通过 Tool Registry 调用业务能力。
- Repository 不暴露给 API 或 Agent 直接使用。

## 7. 前端计划

第一版路由：

```text
/auth/login
/trips
/trips/new
/trips/:tripId
/trips/:tripId/candidates/:candidateId
/trips/:tripId/versions
/agent-runs/:runId
/settings/preferences
```

页面职责：

- `/auth/login`：登录页，获取 JWT。
- `/trips`：旅行计划列表，展示计划状态。
- `/trips/new`：创建计划页，结构化表单 + 自然语言补充。
- `/trips/:tripId`：正式行程详情页，展示 active version 的当前结构化投影。
- `/trips/:tripId/candidates/:candidateId`：候选草案审核页。
- `/trips/:tripId/versions`：历史版本页和回滚入口。
- `/agent-runs/:runId`：Agent 执行详情页。
- `/settings/preferences`：用户全局偏好设置。

前端状态管理：

```text
服务端状态：TanStack Query
表单状态：Ant Design Form
本地 UI 状态：React useState / useReducer
```

第一版不引入 Redux / Zustand。

## 8. 后端计划

后端分层：

```text
API Layer -> Service Layer -> Repository Layer -> Model Layer
```

职责：

- API Layer：请求解析、认证、响应格式、HTTP 错误映射。
- Service Layer：权限校验、业务规则、事务边界、冲突检测、版本发布、回滚。
- Repository Layer：数据访问。
- Model Layer：SQLAlchemy 模型、字段、索引、数据库约束。

API 分组：

```text
/api/v1/auth
/api/v1/users/me
/api/v1/preferences
/api/v1/trips
/api/v1/trip-candidates
/api/v1/trip-versions
/api/v1/agent-runs
```

关键 API：

```text
POST   /api/v1/auth/login
GET    /api/v1/users/me
GET    /api/v1/preferences
PUT    /api/v1/preferences
GET    /api/v1/trips
POST   /api/v1/trips
GET    /api/v1/trips/{trip_id}
PATCH  /api/v1/trips/{trip_id}
POST   /api/v1/trips/{trip_id}/generate
POST   /api/v1/trips/{trip_id}/adjust
GET    /api/v1/trips/{trip_id}/candidates
GET    /api/v1/trip-candidates/{candidate_id}
POST   /api/v1/trip-candidates/{candidate_id}/validate
POST   /api/v1/trip-candidates/{candidate_id}/publish
POST   /api/v1/trip-candidates/{candidate_id}/discard
GET    /api/v1/trips/{trip_id}/versions
GET    /api/v1/trip-versions/{version_id}
POST   /api/v1/trip-versions/{version_id}/rollback
GET    /api/v1/agent-runs/{run_id}
GET    /api/v1/agent-runs/{run_id}/events
GET    /api/v1/agent-runs/{run_id}/tool-calls
POST   /api/v1/agent-runs/{run_id}/cancel
```

## 9. 领域模型

核心对象：

```text
User
UserPreference
Trip
TripPreference
TripDay
ItineraryItem
BudgetItem
TripCandidate
TripVersion
Conflict
AgentRun
AgentRunEvent
ToolCall
AgentTrace
RagDocument
RagChunk
```

`Trip.status`：

```text
draft
generating
reviewing
active
archived
```

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

## 10. Candidate / Version / 当前投影

第一版采用 Draft / Plan / Publish 模式：

```text
TripCandidate = Draft / Plan
validate = Dry-run
publish = Apply
TripVersion = Published Revision
TripDay / ItineraryItem / BudgetItem = 当前正式投影
```

`TripCandidate` 保存候选快照：

```text
id
trip_id
source_type: agent | user_edit | regenerate | partial_adjustment
source_agent_run_id
base_version_id
status: draft | validating | ready | blocked | published | discarded
itinerary_snapshot
budget_snapshot
preference_snapshot
validation_summary
created_by
created_at
updated_at
```

`TripVersion` 保存发布快照：

```text
id
trip_id
version_no
source_type: user | agent | rollback
source_agent_run_id
itinerary_snapshot
budget_snapshot
preference_snapshot
conflict_snapshot
ignored_warning_conflict_ids
publish_note
created_by
created_at
```

当前正式行程使用结构化表：

```text
TripDay
ItineraryItem
BudgetItem
```

## 11. 发布事务

发布 Candidate 必须在单个数据库事务中完成。

事务内步骤：

```text
1. 权限校验
2. Trip 行级锁定
3. Candidate 状态校验
4. 重新执行确定性校验
5. blocking / warning 发布规则校验
6. 创建 TripVersion
7. 重建 TripDay / ItineraryItem / BudgetItem 当前投影
8. 更新 Trip.active_version_id / Trip.status
9. 标记 Candidate = published
10. 写入发布审计记录
```

同一个 Trip 同一时间只能有一个 publish 事务成功。

## 12. 冲突检测

冲突级别：

```text
blocking  阻塞发布，必须修复
warning   允许发布，但必须用户显式确认忽略
info      仅提示，不影响发布
```

第一版冲突类型：

```text
time_overlap
insufficient_transfer
closed_place
budget_exceeded
weather_risk
pace_overload
missing_required_place
avoidance_violation
```

发布规则：

```text
存在 blocking -> 禁止发布
存在 warning -> 用户确认忽略后可发布
只有 info 或无冲突 -> 可直接发布
```

发布时后端必须重新校验，不能只信任前端展示结果。

## 13. 外部数据 Provider

第一版采用 Provider Interface + Mock/Seed Implementation。

Provider 接口：

```text
PlaceProvider
WeatherProvider
TransferTimeProvider
OpeningHoursProvider
```

第一版实现：

```text
SeedPlaceProvider
MockWeatherProvider
MockTransferTimeProvider
MockOpeningHoursProvider
```

后续可替换为真实 Provider。

## 14. Redis 与 Celery

Redis 用于：

```text
天气缓存
地点查询缓存
交通时间估算缓存
开放时间缓存
Agent 会话中间状态
Celery Broker
```

Celery 任务：

```text
run_agent_task
validate_candidate_task
sync_weather_cache_task
archive_old_agent_events_task
build_rag_embedding_task
summarize_trip_version_task
```

发布正式版本不放在 Celery 异步任务中，应由 API 请求内事务完成。

## 15. 安全与权限

第一版安全边界：

```text
单用户数据隔离 + JWT 认证 + Service 层统一鉴权 + Agent Tool 带上下文鉴权
```

用户只能访问自己的 Trip、Candidate、Version、AgentRun、ToolCall、Trace、Preference 和私有 RAG 数据。

日志脱敏：不记录明文 token、API key；Provider 原始请求默认不完整落库。

## 16. 测试计划

后端测试：

- Service 单元测试。
- Repository 集成测试。
- API 测试。
- Candidate publish 事务测试。
- ConflictDetector 测试。
- Agent Runtime 假 Provider 测试。
- Tool Registry 权限测试。

前端测试：

- 关键页面组件测试。
- API client 测试。
- TanStack Query hook 测试。
- Candidate 发布流程测试。

端到端测试：

```text
创建 Trip -> AgentRun -> TripCandidate -> Validate -> Publish -> TripVersion
```

优先级最高的回归用例：

```text
blocking 冲突不能发布
warning 未确认不能发布
warning 确认后可以发布
发布后创建 TripVersion 并重建当前投影
回滚创建新版本而不是覆盖历史版本
Agent 不能越权读取其他用户 Trip
Agent 输出非法 JSON 会失败并记录事件
```

## 17. MVP 阶段拆解

### 阶段 1：基础工程与认证

- 初始化后端 FastAPI 项目。
- 初始化前端 React/Vite 项目。
- 配置 Docker Compose：PostgreSQL、Redis、backend、worker、frontend。
- 配置 Alembic。
- 实现 JWT 认证。

### 阶段 2：Trip 与 Preference

- 实现 UserPreference。
- 实现 Trip。
- 实现 TripPreference。
- 实现旅行计划列表、创建、详情。
- 前端完成 `/trips`、`/trips/new`、`/trips/:tripId` 基础页面。

### 阶段 3：Candidate / Version / Publish

- 实现 TripCandidate。
- 实现 TripVersion。
- 实现 TripDay / ItineraryItem / BudgetItem 当前投影。
- 实现 validate / publish / discard。
- 实现回滚。

### 阶段 4：冲突检测

- 实现 ConflictDetector。
- 支持 blocking / warning / info。
- 支持时间重叠、交通不足、开放时间、预算、天气、节奏、必去地点、避雷项。

### 阶段 5：Agent 最小闭环

- 实现 AgentRun。
- 实现 AgentRunEvent。
- 实现 ToolCall。
- 实现 Agent Runtime 最小流程。
- 实现 Mock Provider。
- 实现 Structured Output 校验。
- Agent 生成 TripCandidate。

### 阶段 6：RAG 与 Trace

- 启用 pgvector。
- 实现 RagDocument / RagChunk。
- 导入 seed 城市攻略、景点说明、餐厅介绍。
- 实现用户偏好和历史版本摘要入库。
- 实现 AgentTrace。

### 阶段 7：前端审核体验

- 实现 Candidate 审核页。
- 实现冲突展示。
- 实现版本历史页。
- 实现 AgentRun 详情页。
- 实现发布、废弃、回滚交互。

## 18. 文档拆分

本文件 `plan.md` 负责整体项目计划、前后端架构、领域模型、MVP 阶段和验收标准。

Agent 子系统的详细设计放在 `agent.md`。
