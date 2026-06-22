# ProjectBrain 本地应用与 Brain Explorer 重设计

| 字段 | 内容 |
| --- | --- |
| 状态 | 待评审草案 |
| 日期 | 2026-06-22 |
| 所属项目 | ProjectBrain |
| 范围 | 产品重新定位、本地应用模式、项目大脑存储、Brain Explorer 可视化页面 |

## 1. 问题背景

ProjectBrain 最初是一个面向 AI 编程助手的本地项目认知层。当前实现已经能基于 CodeGraph facts 生成 Context Pack 和 Impact Analysis，但产品方向逐渐偏向“给 Agent 输出上下文和影响分析”，而不是最初设想的“随项目存在、可持续积累的项目大脑”。

新的目标不是只增强 Agent 输出，而是做一个本地项目知识库，把以下内容组合起来：

- 基于 CodeGraph 的代码结构索引。
- 从对话和人工经验中沉淀的长期项目知识。
- 可搜索、可评审、可迁移的项目记忆。
- 开发前基于项目大脑的上下文检索。
- 代码变更后基于项目大脑的影响分析。
- 一个可视化本地应用，让用户选择工程并查看该工程的知识库内容。

## 2. 产品重新定位

ProjectBrain 应重新定位为：

> 一个本地项目大脑应用。它为特定项目保存代码事实、对话记忆、人工确认的约束、决策、坑点、流程、风险和测试经验，并帮助开发者与 AI agent 检索项目知识、评估代码影响、在代码变化后维护项目大脑。

新的产品中心是 **Project Brain Knowledge Base（项目大脑知识库）**。现有的 Context Pack 和 Impact Analysis 不再是产品本体，而是基于项目大脑之上的应用层能力。

## 3. 目标用户流程

### 3.1 本地应用流程

```text
打开 ProjectBrain
  -> 选择或打开一个本地工程
  -> ProjectBrain 检查代码索引状态和 Brain 状态
  -> 进入该工程的 Brain Explorer
  -> 搜索、筛选、查看、评审项目知识
  -> Codex/MCP 将长期知识写入同一份项目 Brain
  -> 影响分析同时读取代码 facts 和 Brain knowledge
```

### 3.2 第一阶段实现流程

第一阶段先提供本地应用模式命令：

```bash
projectbrain app
```

这个命令应该完成：

1. 自动启动本地 FastAPI/HTMX 应用。
2. 自动打开浏览器到 Project Picker 页面。
3. 让用户选择或打开一个工程目录。
4. 初始化或定位该工程的 `.projectbrain/brain/` 存储。
5. 跳转到该工程的 Brain Explorer 页面。

这个阶段用于快速验证产品流程。真正的桌面应用壳可以在本地 Web 应用体验稳定后再做。

### 3.3 后续桌面应用流程

后续可以用 PyWebView、Tauri 或 Electron 等桌面壳封装同一套后端和 UI：

```text
双击 ProjectBrain.app
  -> Project Picker
  -> Brain Explorer
```

最终用户不需要手动运行 `uvicorn`，不需要记 localhost 地址，也不需要自己管理 Web 服务进程。

## 4. 架构概览

```text
ProjectBrain 本地应用
├── App Registry
│   └── 最近打开的工程和全局偏好
├── Project Picker UI
│   └── 打开/选择本地工程
├── Project Brain Store
│   └── 项目内长期知识库
├── Code Facts Cache
│   └── CodeGraph 生成的实体和关系
├── Brain Explorer UI
│   └── 搜索/筛选/详情/评审项目知识
├── CLI
│   └── app、brain remember/list/search/export/import
└── MCP Server
    └── remember/search/list/review/task-context/impact
```

App、CLI、API 和 MCP Server 必须共享同一份项目内 Brain 数据。

## 5. 数据位置设计

ProjectBrain 需要区分“属于项目的长期知识”和“属于应用的偏好/缓存”。

### 5.1 项目内长期 Brain

存放在被选择的工程目录下：

```text
<project>/.projectbrain/brain/
  manifest.json
  knowledge_units.jsonl
  concepts.jsonl
  conversations.jsonl
  links.jsonl
```

这个目录是真正可迁移的项目大脑。它可以复制、导出、导入，也可以由用户按需纳入版本管理。

### 5.2 项目内生成数据

存放在：

```text
<project>/.projectbrain/cache/
  code_facts.json
  retrieval_index.json

<project>/.projectbrain/runs/
  context-pack-latest.json
  impact-analysis-latest.json
```

缓存和运行产物可以重新生成，不应该被视为长期知识的唯一来源。

### 5.3 应用全局 Registry

长期建议放在系统合适的本地应用数据目录，例如 macOS：

```text
~/Library/Application Support/ProjectBrain/recent_projects.json
```

第一阶段如果 OS 路径抽象还没实现，也可以先放在配置的 `--store-root` 下。

Registry 只保存应用级元数据：

```json
{
  "recent_projects": [
    {
      "project_id": "codeunderstand",
      "name": "codeunderstand",
      "path": "/Users/a58/personal/codeunderstand",
      "last_opened_at": "2026-06-22T00:00:00Z",
      "brain_status": "ready",
      "codegraph_status": "ready"
    }
  ]
}
```

项目知识不能只保存在全局 Registry 里，必须保存在项目自己的 Brain Store 中。

## 6. Brain 数据模型

### 6.1 KnowledgeUnit

`KnowledgeUnit` 是项目大脑的最小长期记忆单元。

```json
{
  "id": "ku_refund_fee_settlement_constraint",
  "type": "constraint",
  "title": "退款手续费不能影响结算本金",
  "statement": "Refund handling fee must not change settlement principal amount.",
  "summary": "退款手续费需要单独记账，不能影响结算本金。",
  "tags": ["refund", "settlement", "fee"],
  "applies_to": ["refund", "settlement", "RefundService.calculate"],
  "related_code": [
    {
      "kind": "symbol",
      "stable_key": "method:RefundService.calculate",
      "file": "service/refund/RefundService.java",
      "symbol": "RefundService.calculate"
    }
  ],
  "evidence": [
    {
      "type": "conversation",
      "session_id": "session_2026_06_22_refund_fee",
      "summary": "用户在退款手续费设计讨论中确认了这个约束。"
    }
  ],
  "confidence": 0.92,
  "risk_level": "high",
  "review_state": "human_confirmed",
  "staleness": {
    "state": "fresh",
    "reason": null
  },
  "created_at": "2026-06-22T00:00:00Z",
  "updated_at": "2026-06-22T00:00:00Z"
}
```

### 6.2 知识类型

第一版支持以下类型：

| 类型 | 含义 |
| --- | --- |
| `constraint` | 代码变更不能违反的约束或不变量。 |
| `decision` | 架构、产品、技术或业务决策。 |
| `gotcha` | 已知坑点、反直觉行为或历史注意事项。 |
| `workflow` | 业务流程或技术流程说明。 |
| `risk` | 已知风险区域，需要谨慎处理。 |
| `test_guidance` | 测试策略或重要测试用例建议。 |
| `open_question` | 尚未解决的问题。 |
| `concept_note` | 领域概念解释。 |
| `incident` | 历史 bug、故障或根因记录。 |

### 6.3 评审状态

第一版支持以下状态：

| 状态 | 含义 |
| --- | --- |
| `draft` | 本地创建但尚未被信任。 |
| `ai_inferred` | AI 推断产生，尚未确认。 |
| `human_review_required` | 需要人工评审后才能作为高可信知识使用。 |
| `human_confirmed` | 已由人工确认，可以作为长期知识使用。 |
| `rejected` | 已评审并拒绝。 |
| `archived` | 历史知识，默认不参与 active retrieval。 |

### 6.4 过期状态

第一版支持以下状态：

| 状态 | 含义 |
| --- | --- |
| `fresh` | 暂无过期信号。 |
| `maybe_stale` | 相关代码发生变化，建议人工复查。 |
| `stale` | 已知过期。 |
| `source_missing` | 关联的文件或符号在当前导入 facts 中不存在。 |

## 7. Brain Explorer UI

第一版可视化入口是 Brain Explorer，而不是复杂图谱。

### 7.1 Project Picker 页面

路由：

```text
GET /ui/app/projects
```

用途：

- 展示最近打开的工程。
- 打开一个本地工程路径。
- 展示工程状态：Brain 是否 ready、是否需要初始化、CodeGraph 是否缺失、stale knowledge 数量等。
- 跳转到 Brain Explorer。

### 7.2 Brain Explorer 页面

路由：

```text
GET /ui/projects/{project_id}/brain
```

布局：

```text
顶部：项目名称、Brain summary counts
左侧：type/review/staleness/tag filters
中间：搜索框和知识列表
右侧：选中知识详情
```

第一版必须展示：

- 总知识数量。
- 按知识类型统计。
- 按评审状态统计。
- 按过期状态统计。
- 搜索框。
- 类型过滤。
- 评审状态过滤。
- 过期状态过滤。
- 知识卡片/列表。
- 详情面板。

### 7.3 知识卡片

每个知识卡片展示：

- 标题或短 statement。
- 类型。
- 评审状态。
- 风险等级。
- 标签。
- applies-to 摘要。
- 关联代码数量。
- 更新时间。

### 7.4 知识详情面板

详情面板展示：

- 标题。
- 类型。
- Statement。
- Summary。
- 标签。
- Applies-to。
- 关联代码引用。
- Evidence。
- 关联对话。
- 评审状态。
- Confidence。
- 风险等级。
- 过期状态。
- 创建/更新时间。

### 7.5 第一版页面操作

第一版 UI 支持轻量评审操作：

- 标记为 `human_confirmed`。
- 标记为 `rejected`。
- 标记为 `archived`。
- 标记为 `maybe_stale` 或 `fresh`。

完整富文本编辑、新增复杂知识等能力可以后置。第一阶段新增知识主要通过 CLI/MCP 完成。

## 8. API 设计

### 8.1 App API

```text
GET  /api/v1/app/projects
POST /api/v1/app/projects/open
```

`POST /api/v1/app/projects/open` 请求：

```json
{
  "project_path": "/path/to/project",
  "project_id": "optional_id"
}
```

返回：

```json
{
  "project": {
    "project_id": "codeunderstand",
    "name": "codeunderstand",
    "path": "/Users/a58/personal/codeunderstand"
  },
  "brain_status": "ready",
  "codegraph_status": "missing | ready | stale",
  "next_url": "/ui/projects/codeunderstand/brain"
}
```

### 8.2 Brain API

```text
GET   /api/v1/projects/{project_id}/brain/summary
GET   /api/v1/projects/{project_id}/brain/knowledge
GET   /api/v1/projects/{project_id}/brain/knowledge/{knowledge_id}
POST  /api/v1/projects/{project_id}/brain/knowledge
PATCH /api/v1/projects/{project_id}/brain/knowledge/{knowledge_id}
```

列表接口 query 参数：

```text
q
type
review_state
staleness
risk_level
tag
limit
offset
```

## 9. CLI 设计

### 9.1 本地应用模式

```bash
projectbrain app
```

参数：

```bash
projectbrain app --host 127.0.0.1 --port 0
projectbrain app --project /path/to/project
```

行为：

- 启动本地 API/UI server。
- 如果未指定端口，则自动选择可用端口。
- 默认自动打开浏览器。
- 如果传入 `--project`，则直接打开或初始化该工程，并跳转到它的 Brain Explorer。

### 9.2 Brain 命令

```bash
projectbrain brain init <project_path> --id my_project

projectbrain brain remember my_project \
  --type constraint \
  --statement "Refund handling fee must not change settlement principal amount." \
  --applies-to refund \
  --applies-to settlement \
  --review-state human_confirmed

projectbrain brain list my_project
projectbrain brain search my_project "refund fee settlement"
projectbrain brain export my_project --output my_project.projectbrain.zip
projectbrain brain import --input my_project.projectbrain.zip --id my_project
```

现有 `claim` 命令继续保留以保持兼容，但后续应逐步映射到 `KnowledgeUnit`。

## 10. MCP 设计

第一批 Brain-oriented MCP 工具如下。

### 10.1 `projectbrain_remember`

将长期知识写入当前项目的 Brain。

```json
{
  "project_id": "my_project",
  "type": "constraint",
  "statement": "Refund handling fee must not change settlement principal amount.",
  "applies_to": ["refund", "settlement"],
  "review_state": "human_confirmed",
  "tags": ["refund", "fee"],
  "source": ["conversation://current"]
}
```

### 10.2 `projectbrain_search_brain`

搜索项目长期知识。

```json
{
  "project_id": "my_project",
  "query": "refund fee settlement",
  "types": ["constraint", "decision", "gotcha"],
  "limit": 10
}
```

### 10.3 `projectbrain_list_memory`

按过滤条件列出 Brain 知识。

```json
{
  "project_id": "my_project",
  "types": ["constraint"],
  "review_state": "human_confirmed",
  "include_archived": false
}
```

### 10.4 `projectbrain_review_memory`

更新知识的评审状态或过期状态。

```json
{
  "project_id": "my_project",
  "memory_id": "ku_refund_fee_settlement_constraint",
  "review_state": "human_confirmed"
}
```

现有 Context Pack 和 Impact MCP 工具后续应变成 brain-aware，输出相关 `KnowledgeUnit`。

## 11. 检索设计

第一版使用本地 lexical scoring，不依赖 embedding、向量数据库或网络服务。

搜索匹配字段：

- `title`
- `statement`
- `summary`
- `tags`
- `applies_to`
- 关联代码文件路径
- 关联 symbol 名称
- evidence summary

加权策略：

- 精确 tag 命中加权。
- 精确 applies-to 命中加权。
- `human_confirmed` 知识加权。
- 对影响敏感任务，`constraint` / `risk` / `gotcha` 类型加权。
- 高风险知识加权。

## 12. Brain-aware Context 与 Impact

### 12.1 Context

现有 Context Pack 应升级，加入：

- `relevant_knowledge_units`
- `relevant_constraints`
- `relevant_decisions`
- `relevant_gotchas`
- `relevant_test_guidance`
- `open_questions`

当前 `experience_claims` section 应成为相关 `KnowledgeUnit` 的兼容视图。

### 12.2 Impact

现有 Impact Analysis 应升级，加入：

- `affected_knowledge_units`
- `possibly_stale_knowledge`
- `violated_or_relevant_constraints`
- `related_decisions`
- `brain_update_suggestions`

这是 ProjectBrain 支持“超越代码图邻居的全局影响评估”的核心机制。

## 13. 迁移与兼容

现有 `experience_claims.json` 不能丢弃。

兼容计划：

1. 保持旧 claim 命令可用。
2. 将每条 experience claim 映射成 `KnowledgeUnit` 视图。
3. 新的 brain 命令写入 `knowledge_units.jsonl`。
4. 过渡期间 Context/Impact 同时读取两种来源。
5. 后续增加迁移命令：

```bash
projectbrain brain migrate-claims my_project
```

## 14. 分阶段实施计划

### Phase 1：Brain Core + Local App Mode

必须包含：

- `KnowledgeUnit` 模型。
- 项目内 `.projectbrain/brain/` 布局。
- 基于 JSONL 的 Brain Repository。
- Brain summary/list/search/detail/update 函数。
- `projectbrain app` 命令，启动 UI 并打开 Project Picker。
- Project Picker route。
- Brain Explorer route。
- CLI `brain remember/list/search`。
- MCP `projectbrain_remember`、`projectbrain_search_brain`、`projectbrain_list_memory`、`projectbrain_review_memory`。

### Phase 2：Brain-aware Context and Impact

必须包含：

- Context Pack 包含相关 Brain knowledge。
- Impact Analysis 包含 affected knowledge 和 stale suggestions。
- Git diff impact 使用 Brain knowledge。
- 测试覆盖 code + brain 组合影响分析。

### Phase 3：Export/Import and Migration

必须包含：

- Brain export package。
- Brain import。
- Claim migration command。
- App UI 中的 export/import。

### Phase 4：Desktop Wrapper

必须包含：

- PyWebView 或 Tauri 原型。
- 自动管理后端生命周期。
- 优先打包 macOS 本地应用。

### Phase 5：Relationship Graph and Advanced Review

后续可选范围：

- 知识-代码关系图。
- 对话记忆收件箱。
- Staleness review queue。
- Brain health score。
- 可选 embedding index。

## 15. 测试策略

### 单元测试

- `KnowledgeUnit` 校验与默认值。
- JSONL repository append/list/update 行为。
- 搜索评分与过滤。
- Summary stats。
- App project registry。

### API 测试

- 打开工程。
- Brain summary。
- Brain list/search/detail。
- Brain update review state。

### CLI 测试

- `projectbrain brain remember` 写入知识。
- `projectbrain brain search` 找到知识。
- `projectbrain app --project` 能解析目标工程。

### MCP 测试

- `projectbrain_remember` 写入本地 brain memory。
- `projectbrain_search_brain` 返回该知识。
- `projectbrain_review_memory` 更新状态。

### UI Smoke Tests

- Project Picker 可以渲染。
- Brain Explorer 可以渲染。
- 搜索/过滤后显示期望内容。
- Detail panel 能显示选中知识。

## 16. 第一版非目标

第一版不做：

- 原生桌面应用打包。
- 复杂关系图可视化。
- ProjectBrain 内部自动调用 LLM 提取知识。
- 向量数据库。
- 云同步。
- 多人协作。
- 完整富文本知识编辑器。
- 认证和权限系统。

## 17. 待决策问题

1. 第一版 App Registry 放在 OS app data 目录，还是先放在 `--store-root` 下。
2. `.projectbrain/brain/` 默认是否建议纳入 Git，还是只建议手动导出。
3. 第一版 UI 是否支持手动创建 KnowledgeUnit，还是只支持查看和轻量 review。
4. Desktop wrapper 阶段优先选择 PyWebView 还是 Tauri。

## 18. 推荐第一版切入点

推荐第一版按以下顺序实现：

1. 实现 Brain Core 和 JSONL store。
2. 实现 CLI/MCP memory 命令。
3. 实现 local app mode，包括 Project Picker 和 Brain Explorer。
4. 新知识创建第一阶段主要通过 CLI/MCP 完成。
5. UI 支持读取、搜索、筛选、查看和轻量评审知识。
6. 关系图和桌面打包等能力等 local app mode 验证后再做。
