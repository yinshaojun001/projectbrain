# ProjectBrain 本地应用与 codex-brain 会话捕获重设计

| 字段 | 内容 |
| --- | --- |
| 状态 | 待评审草案 |
| 日期 | 2026-06-22 |
| 所属项目 | ProjectBrain |
| 范围 | 产品重新定位、codex-brain 启动器、显式托管式 Codex 会话捕获、项目大脑存储、Brain Explorer 可视化页面 |

## 1. 问题背景

ProjectBrain 最初希望成为“项目大脑”：它不只索引代码，还要把开发过程中产生的项目认知、业务约束、历史决策、坑点和测试经验沉淀成可迁移的本地知识库。

当前实现已经能基于 CodeGraph facts 生成 Context Pack 和 Impact Analysis，但它仍然更像一个给 AI agent 提供单次上下文的工具。真正的难点在于：项目知识往往不是预先写好的文档，而是在用户和 Codex / Claude Code 等 agent 的真实开发对话中逐步产生的。

因此，ProjectBrain 需要解决的核心问题是：

```text
用户在 Codex CLI 中进行开发对话
  -> 对话中产生项目认知和整体结论
  -> ProjectBrain 能捕获本次显式托管的会话
  -> 提取候选知识
  -> 用户在本地 Brain Explorer 中评审
  -> 确认后写入该项目的长期 Brain
  -> 后续开发时用于上下文检索和影响分析
```

## 2. 产品重新定位

ProjectBrain 应重新定位为：

> 一个本地项目大脑应用。它通过 CodeGraph 建立代码索引，通过 codex-brain 显式托管 Codex CLI 会话，从真实开发对话中提取候选项目知识，并将人工确认后的知识保存为项目内可迁移的长期 Brain。

新的产品中心是 **Project Brain Knowledge Base（项目大脑知识库）**。

`codex-brain` 是第一阶段最重要的入口：

```text
codex        = 普通 Codex CLI 会话
codex-brain  = 带 ProjectBrain 启动、会话捕获、知识提取和 Brain Explorer 的 Codex CLI 会话
```

Context Pack 和 Impact Analysis 仍然保留，但它们应逐步变成基于项目 Brain 的应用层能力，而不是产品本体。

## 3. 目标用户流程

### 3.1 codex-brain 主流程

用户在工程目录中运行：

```bash
codex-brain
```

流程：

```text
codex-brain
  -> 识别当前工程
  -> 初始化或加载 <project>/.projectbrain/brain/
  -> 启动 ProjectBrain 本地应用后端
  -> 打开 Brain Explorer 页面
  -> 以 PTY 子进程启动 Codex CLI
  -> 捕获本次由 codex-brain 显式托管的用户输入和 Codex 输出
  -> 创建 ConversationSession
  -> 会话结束时提取整体结论和候选项目知识
  -> 写入 Memory Candidate Queue
  -> Brain Explorer 显示“待确认知识”
  -> 用户确认后写入 KnowledgeUnit
```

### 3.2 本地应用流程

```text
打开 ProjectBrain UI
  -> 选择或打开一个本地工程
  -> ProjectBrain 检查代码索引状态和 Brain 状态
  -> 进入该工程的 Brain Explorer
  -> 搜索、筛选、查看、评审项目知识
  -> 查看 codex-brain 会话提取出的候选知识
  -> 将确认后的候选写入项目 Brain
```

### 3.3 后续桌面应用流程

后续可以用 PyWebView、Tauri 或 Electron 等桌面壳封装同一套后端和 UI：

```text
双击 ProjectBrain.app
  -> Project Picker
  -> Brain Explorer
```

但第一阶段不优先做桌面打包。第一阶段优先验证 `codex-brain` 和 Brain Explorer 的闭环。

## 4. 关键设计原则

### 4.1 显式托管，不做后台监听

ProjectBrain 不应后台监听所有终端，也不应偷偷读取普通 `codex` 会话。

第一版只捕获：

```text
由用户显式运行 codex-brain 后，由 codex-brain 启动并托管的 Codex CLI 子进程。
```

这保证了隐私边界清晰：

```text
普通 codex 不被捕获
codex-brain 会话才被捕获
```

### 4.2 对话不直接污染长期 Brain

从对话中提取出的内容不能全部直接写入长期知识库。默认流程是：

```text
Conversation Transcript / Summary
  -> MemoryCandidate
  -> 人工评审
  -> KnowledgeUnit
```

只有用户明确确认的内容，或用户在 UI 中确认的候选，才能成为高可信长期知识。

### 4.3 默认不保存完整 transcript 到可迁移 Brain

完整会话内容可能包含隐私、临时信息或敏感内容。第一版默认：

```text
不把完整 transcript 写入 <project>/.projectbrain/brain/
```

长期 Brain 中只保存：

- ConversationSession 摘要。
- MemoryCandidate。
- KnowledgeUnit。
- 简短 evidence summary。

完整 transcript 如需保存，只能放在本地 session cache，并受配置控制。

### 4.4 Codex 负责理解对话，ProjectBrain 负责沉淀和治理

第一版不让 ProjectBrain 自己调用 LLM 自动理解完整对话。更现实的方式是：

```text
Codex 拥有当前对话上下文
  -> codex-brain 在退出时让 Codex 输出结构化候选记忆
  -> ProjectBrain 负责解析、校验、去重、入候选队列、UI 评审和持久化
```

## 5. 架构概览

```text
User Terminal
  ↓
codex-brain
  ├── Project Detector
  │   └── 识别当前 git/project path
  ├── ProjectBrain App Launcher
  │   └── 启动本地 API/UI 并打开 Brain Explorer
  ├── Codex CLI Launcher
  │   └── 以 PTY 子进程启动 codex
  ├── Session Recorder
  │   └── 捕获本次显式托管会话的输入/输出
  ├── Conversation Extractor
  │   └── 会话结束时提取整体结论和候选知识
  └── ProjectBrain Client
      └── 写入 ConversationSession / MemoryCandidate

ProjectBrain Local App
  ├── Project Picker UI
  ├── Brain Explorer UI
  ├── Memory Candidate Queue
  ├── KnowledgeUnit Store
  ├── Code Facts Cache
  ├── CLI / MCP
  └── Brain-aware Context / Impact
```

## 6. 数据位置设计

ProjectBrain 需要区分“属于项目的长期知识”、“属于项目的会话缓存”和“属于应用的全局偏好”。

### 6.1 项目内长期 Brain

存放在被选择的工程目录下：

```text
<project>/.projectbrain/brain/
  manifest.json
  knowledge_units.jsonl
  memory_candidates.jsonl
  conversations.jsonl
  concepts.jsonl
  links.jsonl
```

这个目录是真正可迁移的项目大脑。它可以复制、导出、导入，也可以由用户按需纳入版本管理。

### 6.2 项目内会话缓存

codex-brain 会话缓存放在：

```text
<project>/.projectbrain/sessions/
  session_2026-06-22T10-30-00_codex/
    session.json
    transcript.raw.log
    transcript.cleaned.md
    extraction_prompt.md
    extraction_output.raw
    candidates.json
```

默认策略：

```text
store_full_transcript = false
```

如果关闭完整 transcript 保存，退出提取后可以删除 `transcript.raw.log`，只保留摘要、候选和必要 evidence。

### 6.3 项目内生成数据

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

### 6.4 应用全局 Registry

长期建议放在系统合适的本地应用数据目录，例如 macOS：

```text
~/Library/Application Support/ProjectBrain/recent_projects.json
```

Registry 只保存最近工程、窗口偏好、全局设置等应用级元数据，不保存项目长期知识。

## 7. Brain 数据模型

### 7.1 KnowledgeUnit

`KnowledgeUnit` 是项目大脑的正式长期知识单元。

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
  "source": {
    "kind": "conversation",
    "session_id": "session_2026_06_22_refund_fee",
    "candidate_id": "mc_refund_fee_constraint",
    "client": "codex-brain"
  },
  "evidence": [
    {
      "type": "conversation_summary",
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

### 7.2 MemoryCandidate

`MemoryCandidate` 是从 Codex 会话中提取出的候选知识，默认需要人工评审。

```json
{
  "candidate_id": "mc_refund_fee_constraint",
  "project_id": "my_project",
  "session_id": "session_2026_06_22_refund_fee",
  "proposed_unit": {
    "type": "constraint",
    "title": "退款手续费不能影响结算本金",
    "statement": "Refund handling fee must not change settlement principal amount.",
    "summary": "退款手续费需要单独记账，不能影响结算本金。",
    "tags": ["refund", "fee", "settlement"],
    "applies_to": ["refund", "settlement"],
    "confidence": 0.92,
    "risk_level": "high"
  },
  "evidence": [
    {
      "type": "conversation_excerpt",
      "summary": "用户明确确认了该约束。"
    }
  ],
  "extraction": {
    "method": "codex_brain_exit_extraction",
    "client": "codex-brain",
    "created_at": "2026-06-22T11:20:00Z"
  },
  "review_state": "human_review_required",
  "possible_duplicates": [],
  "conflicts_with": []
}
```

### 7.3 ConversationSession

`ConversationSession` 记录一次由 codex-brain 托管的开发对话摘要。

```json
{
  "session_id": "session_2026_06_22_refund_fee",
  "project_id": "my_project",
  "client": "codex-brain",
  "task": "Add refund handling fee",
  "summary": "本次会话明确了退款手续费不能影响结算本金，并修改了 RefundService。",
  "started_at": "2026-06-22T10:00:00Z",
  "ended_at": "2026-06-22T11:20:00Z",
  "changed_files": [
    "service/refund/RefundService.java"
  ],
  "candidate_ids": [
    "mc_refund_fee_constraint"
  ],
  "knowledge_unit_ids": [
    "ku_refund_fee_settlement_constraint"
  ],
  "privacy": {
    "stores_full_transcript": false,
    "stores_excerpts": true
  }
}
```

### 7.4 知识类型

第一版支持：

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

### 7.5 评审状态

第一版支持：

| 状态 | 含义 |
| --- | --- |
| `draft` | 本地创建但尚未被信任。 |
| `ai_inferred` | AI 推断产生，尚未确认。 |
| `human_review_required` | 需要人工评审后才能作为高可信知识使用。 |
| `human_confirmed` | 已由人工确认，可以作为长期知识使用。 |
| `rejected` | 已评审并拒绝。 |
| `archived` | 历史知识，默认不参与 active retrieval。 |

### 7.6 过期状态

第一版支持：

| 状态 | 含义 |
| --- | --- |
| `fresh` | 暂无过期信号。 |
| `maybe_stale` | 相关代码发生变化，建议人工复查。 |
| `stale` | 已知过期。 |
| `source_missing` | 关联的文件或符号在当前导入 facts 中不存在。 |

## 8. codex-brain 设计

### 8.1 命令

新增独立命令：

```bash
codex-brain
```

常用参数：

```bash
codex-brain --project /path/to/project
codex-brain --no-ui
codex-brain --no-extract
codex-brain --extract-on-exit
codex-brain --codex-command "codex --model ..."
```

### 8.2 启动行为

`codex-brain` 启动时：

1. 识别项目路径，默认使用当前目录向上查找 Git root。
2. 推导或读取 project_id。
3. 确保 `.projectbrain/brain/` 存在。
4. 确保 ProjectBrain 本地 App 后端运行。
5. 打开 Brain Explorer。
6. 创建 `ConversationSession`。
7. 以 PTY 子进程启动 `codex`。
8. 捕获本次托管会话的输入/输出。

### 8.3 退出行为

会话结束时：

```text
Extract project knowledge from this Codex session? [Y/n]
```

如果用户同意：

1. codex-brain 向 Codex 注入提取 prompt，要求输出 JSON。
2. 解析 `session_summary` 和 `candidates`。
3. 保存 `ConversationSession`。
4. 保存 `MemoryCandidate`。
5. 打开 Brain Explorer 的 Needs Review 视图。

如果 JSON 解析失败：

- 保存 raw extraction output。
- 不创建正式 KnowledgeUnit。
- 在 UI 中提示需要手动处理。

### 8.4 PTY Wrapper

第一版建议使用 PTY wrapper 捕获显式托管会话：

```text
codex-brain
  ↓ spawn PTY
codex
```

可选实现：

- Python 标准库 `pty` + `subprocess`。
- 或使用 `pexpect`，但这会引入新依赖。

第一版优先保持简单和可测试。如果 Codex CLI 的 TUI 输出过于复杂，先保证会话可运行和日志可捕获，再逐步增强 transcript 清洗。

### 8.5 Extraction Prompt

退出时注入 Codex 的提取 prompt 应要求只输出 JSON：

```text
You are helping ProjectBrain extract durable project knowledge from this coding session.

Return ONLY JSON.

Extract facts that will remain useful in future work on this project:
- business constraints
- architecture decisions
- gotchas
- workflows
- risks
- test guidance
- domain concepts
- incident/root-cause lessons

Do NOT include:
- secrets or credentials
- temporary task steps
- unverified speculation as confirmed fact
- source code bodies
- private URLs
- generic programming advice

For each candidate include:
type, title, statement, summary, tags, applies_to, confidence, evidence_summary, review_state.

Rules:
- If the user explicitly confirmed it, review_state can be human_confirmed.
- If it is inferred by the assistant, review_state must be human_review_required.
- Prefer concise, durable statements.
```

期望输出：

```json
{
  "session_summary": "...",
  "candidates": [
    {
      "type": "constraint",
      "title": "...",
      "statement": "...",
      "summary": "...",
      "tags": ["..."],
      "applies_to": ["..."],
      "confidence": 0.8,
      "evidence_summary": "...",
      "review_state": "human_review_required"
    }
  ]
}
```

## 9. Brain Explorer UI

第一版可视化入口是 Brain Explorer，同时必须支持查看 codex-brain 产生的待确认知识。

### 9.1 Project Picker 页面

路由：

```text
GET /ui/app/projects
```

用途：

- 展示最近打开的工程。
- 打开一个本地工程路径。
- 展示工程状态：Brain 是否 ready、是否需要初始化、CodeGraph 是否缺失、stale knowledge 数量等。
- 跳转到 Brain Explorer。

### 9.2 Brain Explorer 页面

路由：

```text
GET /ui/projects/{project_id}/brain
```

布局：

```text
顶部：项目名称、Brain summary counts、待确认知识数量
左侧：type/review/staleness/tag filters
中间：搜索框、知识列表、候选知识列表
右侧：选中知识或候选详情
```

第一版必须展示：

- 总知识数量。
- 待确认候选数量。
- 按知识类型统计。
- 按评审状态统计。
- 按过期状态统计。
- 搜索框。
- 类型过滤。
- 评审状态过滤。
- 过期状态过滤。
- 知识卡片/列表。
- MemoryCandidate 卡片/列表。
- 详情面板。

### 9.3 待确认知识视图

Brain Explorer 需要有一个明显入口：

```text
待确认知识 / Needs Review
```

候选卡片展示：

- 候选标题。
- 候选类型。
- confidence。
- 来源 session。
- 提取方式。
- possible duplicates。
- conflicts。

支持操作：

- 确认入库。
- 拒绝。
- 归档。
- 标记为重复。
- 修改 review_state。

第一版不要求完整富文本编辑，但应允许最基本的确认/拒绝。

## 10. API 设计

### 10.1 App API

```text
GET  /api/v1/app/projects
POST /api/v1/app/projects/open
```

### 10.2 Brain API

```text
GET   /api/v1/projects/{project_id}/brain/summary
GET   /api/v1/projects/{project_id}/brain/knowledge
GET   /api/v1/projects/{project_id}/brain/knowledge/{knowledge_id}
POST  /api/v1/projects/{project_id}/brain/knowledge
PATCH /api/v1/projects/{project_id}/brain/knowledge/{knowledge_id}
```

### 10.3 Memory Candidate API

```text
GET   /api/v1/projects/{project_id}/brain/candidates
GET   /api/v1/projects/{project_id}/brain/candidates/{candidate_id}
POST  /api/v1/projects/{project_id}/brain/candidates
PATCH /api/v1/projects/{project_id}/brain/candidates/{candidate_id}
POST  /api/v1/projects/{project_id}/brain/candidates/{candidate_id}/confirm
POST  /api/v1/projects/{project_id}/brain/candidates/{candidate_id}/reject
```

### 10.4 Conversation Session API

```text
GET  /api/v1/projects/{project_id}/brain/sessions
GET  /api/v1/projects/{project_id}/brain/sessions/{session_id}
POST /api/v1/projects/{project_id}/brain/sessions
PATCH /api/v1/projects/{project_id}/brain/sessions/{session_id}
```

## 11. CLI 设计

### 11.1 codex-brain 命令

`codex-brain` 是第一阶段主入口。

```bash
codex-brain
codex-brain --project /path/to/project
codex-brain --no-ui
codex-brain --no-extract
```

### 11.2 projectbrain app

`projectbrain app` 仍然保留，用于只启动本地 UI，不启动 Codex。

```bash
projectbrain app
projectbrain app --project /path/to/project
```

### 11.3 Brain 命令

```bash
projectbrain brain init <project_path> --id my_project
projectbrain brain remember my_project --type constraint --statement "..."
projectbrain brain list my_project
projectbrain brain search my_project "refund fee settlement"
projectbrain brain candidates my_project
projectbrain brain confirm-candidate my_project <candidate_id>
projectbrain brain reject-candidate my_project <candidate_id>
projectbrain brain export my_project --output my_project.projectbrain.zip
projectbrain brain import --input my_project.projectbrain.zip --id my_project
```

## 12. MCP 设计

MCP 仍然有价值，尤其用于 Codex 在会话中主动写入或搜索 Brain。

第一批 Brain-oriented MCP 工具：

### 12.1 `projectbrain_remember`

立即写入长期知识。适合用户明确说“记住”“这是规则”“以后都要注意”等情况。

### 12.2 `projectbrain_propose_memories`

提交候选记忆，不直接进入正式 Brain。

### 12.3 `projectbrain_search_brain`

搜索项目长期知识。

### 12.4 `projectbrain_list_memory_candidates`

列出待确认候选知识。

### 12.5 `projectbrain_review_memory_candidate`

确认、拒绝或更新候选知识。

### 12.6 `projectbrain_begin_session` / `projectbrain_finalize_session`

可选工具，用于让 agent 主动登记和结束一个开发会话。

这些 MCP 能力与 `codex-brain` 共享同一套底层 Memory Service。

## 13. 检索、去重与冲突检测

### 13.1 检索

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

### 13.2 去重

对候选知识生成 normalized key：

```text
type + normalized_statement + tags + applies_to
```

与已有 KnowledgeUnit 和 MemoryCandidate 进行文本重叠、tag 重叠、applies_to 重叠比较。

发现相似项时，不自动合并，而是标记：

```text
possible_duplicates
```

### 13.3 冲突检测

第一版只做保守提示：

- 同一 applies_to。
- 同一 type=constraint。
- statement 中存在明显相反表达或否定关系。

标记为：

```text
conflicts_with
```

最终由用户在 UI 中评审。

## 14. Brain-aware Context 与 Impact

### 14.1 Context

现有 Context Pack 应升级，加入：

- `relevant_knowledge_units`
- `relevant_constraints`
- `relevant_decisions`
- `relevant_gotchas`
- `relevant_test_guidance`
- `open_questions`

当前 `experience_claims` section 应成为相关 `KnowledgeUnit` 的兼容视图。

### 14.2 Impact

现有 Impact Analysis 应升级，加入：

- `affected_knowledge_units`
- `possibly_stale_knowledge`
- `violated_or_relevant_constraints`
- `related_decisions`
- `brain_update_suggestions`

这是 ProjectBrain 支持“超越代码图邻居的全局影响评估”的核心机制。

## 15. 隐私和安全边界

第一版必须遵守：

1. `codex-brain` 只捕获它自己启动的 Codex 子进程。
2. 不捕获普通 `codex`。
3. 不监听其他终端。
4. 不读取系统剪贴板。
5. 不上传 transcript 或知识。
6. 默认不把完整 transcript 放入可迁移 Brain。
7. 不自动把 AI 推断写成 `human_confirmed`。
8. 不保存 secrets、credentials、token、私钥、客户数据。
9. 提取失败时只保存 raw output 到本地 session cache，不创建正式知识。

## 16. 迁移与兼容

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

## 17. 分阶段实施计划

### Phase 1：codex-brain MVP + Brain Core

必须包含：

- `codex-brain` 独立命令。
- 当前工程识别。
- 项目内 `.projectbrain/brain/` 布局。
- `KnowledgeUnit`、`MemoryCandidate`、`ConversationSession` 模型。
- JSONL Brain Repository。
- MemoryCandidate Queue。
- `codex-brain` 启动 ProjectBrain App 后端。
- `codex-brain` 打开 Brain Explorer。
- `codex-brain` 以 PTY 子进程启动 Codex CLI。
- 会话 transcript capture。
- 退出时 extraction prompt。
- 解析 candidates JSON。
- Brain Explorer 展示待确认知识。
- UI 支持确认/拒绝候选。

### Phase 2：Brain Explorer 完整化

必须包含：

- Project Picker。
- Brain summary。
- Knowledge list/search/filter/detail。
- Candidate list/search/filter/detail。
- Session list/detail。
- 轻量 review actions。

### Phase 3：Brain-aware Context and Impact

必须包含：

- Context Pack 包含相关 Brain knowledge。
- Impact Analysis 包含 affected knowledge 和 stale suggestions。
- Git diff impact 使用 Brain knowledge。
- 测试覆盖 code + brain 组合影响分析。

### Phase 4：Export/Import and Migration

必须包含：

- Brain export package。
- Brain import。
- Claim migration command。
- App UI 中的 export/import。

### Phase 5：Desktop Wrapper and Other Agents

必须包含：

- PyWebView 或 Tauri 原型。
- 自动管理后端生命周期。
- 优先打包 macOS 本地应用。
- 后续再考虑 `claude-brain` 或通用 `agent-brain`。

### Phase 6：Relationship Graph and Advanced Review

后续可选范围：

- 知识-代码关系图。
- 对话记忆收件箱增强版。
- Staleness review queue。
- Brain health score。
- 可选 embedding index。

## 18. 测试策略

### 单元测试

- `KnowledgeUnit`、`MemoryCandidate`、`ConversationSession` 校验与默认值。
- JSONL repository append/list/update 行为。
- 搜索评分与过滤。
- 去重与冲突提示。
- transcript 清洗。
- extraction JSON parser。

### CLI 测试

- `codex-brain --project` 能识别目标工程。
- `codex-brain --no-ui --no-extract` 能启动并退出子进程。
- `projectbrain brain candidates` 能列出候选。
- `projectbrain brain confirm-candidate` 能创建 KnowledgeUnit。

### API 测试

- 打开工程。
- Brain summary。
- Brain list/search/detail。
- Candidate list/detail/confirm/reject。
- Session list/detail。

### MCP 测试

- `projectbrain_remember` 写入本地 brain memory。
- `projectbrain_propose_memories` 写入候选。
- `projectbrain_search_brain` 返回相关知识。
- `projectbrain_review_memory_candidate` 更新候选状态并可确认入库。

### UI Smoke Tests

- Project Picker 可以渲染。
- Brain Explorer 可以渲染。
- Needs Review 可以显示候选知识。
- 搜索/过滤后显示期望内容。
- Detail panel 能显示选中知识和候选。

## 19. 第一版非目标

第一版不做：

- 原生桌面应用打包。
- Claude Code 支持。
- 后台监听普通 codex。
- 复杂关系图可视化。
- ProjectBrain 内部自动调用 LLM 提取知识。
- 向量数据库。
- 云同步。
- 多人协作。
- 完整富文本知识编辑器。
- 认证和权限系统。

## 20. 待决策问题

1. 第一版 PTY wrapper 使用标准库 `pty` 还是引入 `pexpect`。
2. 默认是否在退出时自动提取，还是每次询问用户。
3. `store_full_transcript` 默认 false 时，是否保留 cleaned transcript。
4. 第一版 App Registry 放在 OS app data 目录，还是先放在 `--store-root` 下。
5. `.projectbrain/brain/` 默认是否建议纳入 Git，还是只建议手动导出。
6. Desktop wrapper 阶段优先选择 PyWebView 还是 Tauri。

## 21. 推荐第一版切入点

推荐第一版按以下顺序实现：

1. 实现 Brain Core：KnowledgeUnit、MemoryCandidate、ConversationSession、JSONL store。
2. 实现 MemoryCandidate 的 list/confirm/reject。
3. 实现 Brain Explorer 的 Needs Review 视图。
4. 实现 `codex-brain` 命令，先支持启动 ProjectBrain UI 和托管 Codex CLI。
5. 实现 transcript capture 和 session 文件。
6. 实现退出时 extraction prompt 和 JSON parser。
7. 将 candidates 写入 Brain，并在 UI 中可见。
8. 后续再让 Context/Impact 使用这些知识。
