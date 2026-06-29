# ProjectBrain Baseline Agent Output Design

| 字段 | 内容 |
| --- | --- |
| 状态 | 待评审草案 |
| 日期 | 2026-06-29 |
| 所属项目 | ProjectBrain |
| 范围 | `baseline show` / `baseline build` 的 Agent 输出格式、CLI 接口统一、最小测试与文档收口 |

## 1. 背景

当前 ProjectBrain 已经具备：

- `intake project` / `intake answer`，用于渐进式沉淀项目基线信息。
- `baseline build`，用于从最新 intake session 重建正式项目基线产物。
- `baseline show`，用于读取当前最新的 `project-baseline-latest.json`。
- `context` / `understand` / `impact` / `impact-diff` 的 `--format agent`，用于向 AI 编程智能体提供紧凑、可直接消费的输出。

但 `baseline` 仍然只有 JSON 输出，没有与其他命令对齐的 Agent 消费出口。这会导致：

- Agent 想消费项目基线时，需要自己理解完整 JSON。
- `baseline` 与其他核心命令的 CLI 体验不一致。
- V1 虽然已经能生成项目基线，但还没有把它变成稳定的“智能体输入物”。

## 2. 目标

本微分支只解决一个问题：

> 让 `baseline show` 和 `baseline build` 也支持 `--format agent`，使 Project Baseline 成为 V1 可直接喂给 AI 智能体的正式出口。

目标效果：

- 用户可以运行 `projectbrain baseline show <project_id> --format agent`。
- 用户可以运行 `projectbrain baseline build <project_id> --format agent`。
- 输出结构与现有 `agent_output.py` 风格一致，面向任务消费而不是持久化细节。
- JSON 默认行为保持不变，不破坏现有调用方。

## 3. 非目标

本次明确不做：

- 不新增 `baseline agent` 独立命令。
- 不改动 `project-baseline-latest.json` 的持久化结构。
- 不引入新的 runtime service 方法来“专门生成” Agent 版 Baseline。
- 不把 Baseline 扩展成 Requirement Intake 或更复杂的治理模型。
- 不顺带做 smoke 测试、release checklist、tag、changelog。

## 4. 方案对比

### 4.1 方案 A：`show/build` 统一支持 `--format agent`（采用）

做法：

- 给 `baseline show` 和 `baseline build` 都增加 `--format` 参数。
- 复用现有 `agent_output.py` 的统一输出入口。
- JSON 仍返回完整 `{artifact_path, baseline}`，Agent 格式返回 `{agent_output: ...}`。

优点：

- 改动最小。
- 命令体验和 `context` / `understand` / `impact` 保持一致。
- 易测试、易文档化、易推广为 V1 正式接口。

缺点：

- 需要现在就固定一个最小可用的 Baseline Agent 结构。

### 4.2 方案 B：只给 `baseline show` 加 `--format agent`

优点：

- 语义更保守，`build` 更像纯构建命令。

缺点：

- 命令面不对称。
- 用户会疑惑 `build` 为什么不能直接返回智能体可消费结果。

### 4.3 方案 C：新增 `baseline agent` 子命令

优点：

- 语义显式。

缺点：

- V1 命令面膨胀。
- 会把一个很小的收口点做成新的入口设计。

结论：

- 采用 `方案 A`，这是 V1 最克制且最一致的做法。

## 5. 设计

### 5.1 CLI 设计

命令保持原样，只补充 `--format`：

```bash
projectbrain baseline show my_project --format agent
projectbrain baseline build my_project --format agent
```

约束：

- `--format` 可选值沿用现有 `OUTPUT_FORMATS`。
- 默认仍然是 `json`。
- 不改变 `baseline build` 的构建行为，只改变输出投影。

### 5.2 输出设计

JSON 输出维持现状：

```json
{
  "artifact_path": ".../project-baseline-latest.json",
  "baseline": {
    "bundle_type": "project_baseline",
    "...": "..."
  }
}
```

Agent 输出定义为：

```json
{
  "agent_output": {
    "artifact_type": "project_baseline",
    "project_id": "my_project",
    "project_summary": "...",
    "project_goal": "...",
    "primary_users": [],
    "core_modules": [],
    "key_flows": [],
    "third_party_integrations": [],
    "high_risk_areas": [],
    "constraints": [],
    "validation_strategy": [],
    "priority_evidence": [],
    "unknowns": [],
    "quality_notes": []
  }
}
```

设计原则：

- 保留 Baseline 的核心认知字段，不暴露构建过程细节。
- 字段名尽量直接复用 Baseline 现有结构，降低转换成本。
- 顶层统一使用 `artifact_type`，与现有 Agent 输出习惯保持一致。

### 5.3 输出转换位置

转换逻辑放在 `packages/runtime/projectbrain_runtime/agent_output.py`：

- 继续由 `format_output()` 统一分发。
- 新增对 `baseline` 结果的识别与投影。
- CLI 不手写 Baseline 的 Agent 结构，只负责把 runtime / repository 结果交给统一 formatter。

这样可以保持：

- 输出结构集中管理。
- 后续如果 `baseline` 字段演进，只需改一处。
- CLI 层仍然保持轻薄。

### 5.4 识别规则

`format_agent_output()` 需要新增一条识别规则：

- 当输入数据包含 `baseline` 字段时，返回 Project Baseline 的 Agent 视图。

优先级要求：

- 不影响现有 `context_pack` 与 `impact_analysis` 分支。
- `baseline` 识别逻辑放在它们之后或之前都可以，但必须保证语义唯一且不会误判。

### 5.5 字段映射

| Baseline 原字段 | Agent 输出字段 | 说明 |
| --- | --- | --- |
| `bundle_type` | `artifact_type` | 固定投影为 `project_baseline` |
| `project_id` | `project_id` | 直接透传 |
| `project_summary` | `project_summary` | 直接透传 |
| `project_goal` | `project_goal` | 直接透传 |
| `primary_users` | `primary_users` | 直接透传 |
| `core_modules` | `core_modules` | 直接透传 |
| `key_flows` | `key_flows` | 直接透传 |
| `third_party_integrations` | `third_party_integrations` | 直接透传 |
| `high_risk_areas` | `high_risk_areas` | 直接透传 |
| `constraints` | `constraints` | 直接透传 |
| `validation_strategy` | `validation_strategy` | 直接透传 |
| `priority_evidence` | `priority_evidence` | 直接透传 |
| `unknowns` | `unknowns` | 直接透传 |
| `quality_notes` | `quality_notes` | 直接透传 |

约束：

- 不输出 `artifact_path` 到 `agent_output` 中，避免把消费重点拉到文件系统路径。
- 若某些字段缺失，转换层返回空数组或 `None`，但不抛异常。

## 6. 测试设计

遵循现有 TDD 纪律，只补最小必需红灯：

### 6.1 CLI 红灯

至少新增两个 CLI 测试：

- `baseline show --format agent` 返回 `agent_output.artifact_type == "project_baseline"`。
- `baseline build --format agent` 在重建 artifact 后返回同样的 Agent 输出结构。

测试重点：

- 输出入口被正确注册。
- 结构字段齐全。
- `project_id`、`project_goal` 等关键字段与实际 intake 结果一致。

### 6.2 Formatter 定向测试

如果现有测试组织允许，可额外补一个更小的 formatter 单测：

- 输入 `{ "baseline": {...} }`
- 断言 `format_output(data, "agent")` 的投影结果符合预期

这不是硬性要求；如果 CLI 红灯已经足够稳定，也可以保持本分支只补 CLI 测试。

## 7. 文档收口

需要同步更新：

- `README.md`
- `docs/projectbrain/local-runtime.md`

至少补充：

- `baseline show ... --format agent`
- `baseline build ... --format agent`
- 一句说明：Baseline 现在也可以用紧凑 Agent 结构输出，便于 AI 编程智能体直接消费。

## 8. 验收标准

本微分支完成时，应满足：

1. `baseline show` 支持 `--format agent`。
2. `baseline build` 支持 `--format agent`。
3. 默认 JSON 输出不变。
4. 现有 `context` / `understand` / `impact` 输出不回归。
5. 新增测试先红后绿。
6. 文档中出现新的 Agent 用法示例。

## 9. 实施边界

这个设计对应一个单独微分支，建议命名：

```text
feat/v1-32-baseline-agent-output
```

执行顺序：

1. 从 `feat/v1-product` 拉新 worktree 和微分支。
2. 先补 CLI 红灯。
3. 最小修改 `agent_output.py` 与 `main.py`。
4. 跑定向测试。
5. 更新文档。
6. 跑回归、诊断、提交、推送、合回 `feat/v1-product`。

## 10. 自检结论

- 范围聚焦：只做 Baseline Agent 输出，不扩散到发布其他事项。
- 接口一致：沿用既有 `--format agent` 机制，不发明新命令。
- 兼容性明确：默认 JSON 输出保持不变。
- 可测试性明确：CLI 红灯即可覆盖主行为。
