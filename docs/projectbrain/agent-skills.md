# ProjectBrain Agent Skills

| Field | Value |
| --- | --- |
| Document | Agent Skills |
| Project | ProjectBrain |
| Status | Draft |
| Last updated | 2026-06-12 |

## 1. 目标

ProjectBrain 的 Agent Skills 是外部 Coding Agent 与 Project Brain 交互的稳定能力边界。

Skills 不直接暴露底层数据库，也不要求 Agent 自己理解完整 Knowledge Graph。它们把项目认知整理成面向任务的上下文、解释、影响分析和维护动作。

## 2. Skill 设计原则

1. **Task-scoped**：每次调用必须围绕具体任务、文件、symbol、diff 或问题。
2. **Source-linked**：返回内容必须保留 source、confidence、lifecycle。
3. **Risk-aware**：高风险约束必须显式返回。
4. **Token-budgeted**：输出必须支持 `max_tokens`。
5. **Actionable**：返回结果应能指导 Agent 下一步读哪些文件、跑哪些测试、避开哪些风险。
6. **No silent certainty**：不确定内容必须标注 confidence 和 review state。

## 3. Skill Catalog

| Skill | 目标 | 典型调用方 |
| --- | --- | --- |
| Understand Project Skill | 新 Agent 快速理解项目整体 | Codex、Claude Code、Cursor |
| Impact Analysis Skill | 分析代码修改、需求或 diff 的影响 | Coding Agent、PR bot |
| Architecture Explanation Skill | 解释系统设计、历史原因、业务流程 | Coding Agent、开发者 |
| Knowledge Maintenance Skill | 更新、审核、清理 Project Brain | Brain Update Agent、维护者 |
| Submit Experience Skill | 录入人工经验、约束、事故学习 | 开发者、Tech Lead |

## 4. Understand Project Skill

### 4.1 用途

帮助首次进入项目的 Agent 快速建立认知。

适用场景：

- “先了解这个项目”。
- “我要修改退款逻辑，先给我上下文”。
- “这个 Java 微服务项目有哪些核心模块？”。

### 4.2 输入

```json
{
  "project_id": "proj_payment",
  "scope": {
    "modules": ["payment-service"],
    "business_concepts": ["Refund"],
    "files": [],
    "symbols": []
  },
  "role": "coding_agent",
  "max_tokens": 8000,
  "include": ["overview", "modules", "flows", "constraints", "risks"]
}
```

### 4.3 输出

```json
{
  "skill": "understand_project",
  "project_id": "proj_payment",
  "summary": "payment-service handles payment creation, callbacks, refunds, and accounting record generation.",
  "module_map": [
    {
      "module": "payment-service",
      "responsibility": "Payment and refund orchestration",
      "confidence": 0.92,
      "sources": ["src_..."]
    }
  ],
  "business_concepts": [
    {
      "name": "Refund",
      "description": "Refund lifecycle including request validation, amount calculation, and accounting record creation.",
      "confidence": 0.78,
      "review_state": "pending"
    }
  ],
  "critical_constraints": [
    {
      "statement": "AccountRecord must not be physically deleted because it is used for financial audit.",
      "risk_level": "high",
      "confidence": 1.0,
      "sources": ["src_adr_0042"]
    }
  ],
  "recommended_entrypoints": [
    {
      "type": "API",
      "name": "POST /api/refunds",
      "handled_by": "RefundController.createRefund"
    }
  ],
  "open_questions": []
}
```

### 4.4 Retrieval Policy

优先级：

1. Human-confirmed constraints。
2. Active facts around requested scope。
3. Confirmed decisions and incident learnings。
4. High-confidence AI understanding。
5. Pending inference, clearly marked。

不得返回：

- `rejected` claim。
- `superseded` claim，除非作为历史解释。
- 无 source 的 inference。

## 5. Impact Analysis Skill

### 5.1 用途

分析一个代码变更、需求或 symbol 修改可能影响什么。

适用场景：

- Agent 准备修改某个文件前。
- PR bot 分析 diff。
- 开发者询问“改这里会影响哪些业务？”。

### 5.2 输入

```json
{
  "project_id": "proj_payment",
  "change": {
    "type": "diff",
    "content": "diff --git ..."
  },
  "scope": {
    "files": [
      "payment-service/src/main/java/com/acme/payment/RefundFeeCalculator.java"
    ],
    "symbols": ["RefundFeeCalculator.calculate"]
  },
  "depth": 4,
  "include": ["code", "data", "api", "message", "business", "constraints", "tests"]
}
```

### 5.3 输出

```json
{
  "skill": "impact_analysis",
  "summary": "The change likely affects refund amount calculation, accounting records, and settlement reconciliation.",
  "changed_entities": [
    {
      "stable_key": "java:method:payment-service:RefundFeeCalculator#calculate",
      "change_type": "modified",
      "confidence": 1.0
    }
  ],
  "affected_modules": ["payment-service", "accounting-service"],
  "affected_business_concepts": ["Refund", "Refund Handling Fee", "Account Record"],
  "affected_tables": [
    {
      "name": "refund_record",
      "access": "WRITE",
      "confidence": 0.93
    },
    {
      "name": "account_record",
      "access": "WRITE",
      "confidence": 0.89
    }
  ],
  "affected_apis": [
    {
      "method": "POST",
      "path": "/api/refunds",
      "handled_by": "RefundController.createRefund"
    }
  ],
  "critical_constraints": [
    {
      "statement": "Accounting records must remain append-only.",
      "risk_level": "high",
      "confidence": 1.0,
      "sources": ["src_..."]
    }
  ],
  "recommended_tests": [
    "RefundServiceTest",
    "RefundFeeCalculatorTest",
    "AccountingRecordIntegrationTest"
  ],
  "review_recommendation": {
    "required": true,
    "reason": "Change touches accounting and settlement concepts."
  }
}
```

### 5.4 Traversal Policy

图遍历默认策略：

- 从 changed symbols 出发。
- 向上找 API、Job、Consumer entrypoints。
- 向下找 CALLS、READS、WRITES、PUBLISHES。
- 横向找 IMPLEMENTS 同一 BusinessConcept 的实体。
- 附加 AFFECTS 到 Decision、Incident、Constraint。

默认深度：

- V0.1: `2`
- V0.2: `3`
- V0.3+: `4`

## 6. Architecture Explanation Skill

### 6.1 用途

解释系统设计、历史原因和业务流程。

适用场景：

- “为什么退款需要写 account_record？”。
- “这个服务为什么拆成 payment 和 accounting？”。
- “支付回调为什么必须幂等？”。

### 6.2 输入

```json
{
  "project_id": "proj_payment",
  "question": "为什么支付回调必须保持幂等？",
  "scope": {
    "business_concepts": ["Payment Callback"],
    "files": []
  },
  "max_tokens": 6000,
  "answer_style": "engineering_explanation"
}
```

### 6.3 输出

```json
{
  "skill": "architecture_explanation",
  "answer": "支付回调必须保持幂等，因为外部支付渠道会在网络失败或超时后重试通知，同一支付单可能收到多次 callback。系统通过 payment_order 状态机和 callback_log 去重，避免重复记账。",
  "evidence": [
    {
      "type": "FACT",
      "statement": "PaymentCallbackController delegates callback processing to PaymentCallbackService.",
      "confidence": 1.0,
      "sources": ["src_..."]
    },
    {
      "type": "INCIDENT_LEARNING",
      "statement": "A previous duplicate callback incident caused duplicate accounting records.",
      "confidence": 1.0,
      "sources": ["incident_2024_..."]
    }
  ],
  "related_entities": ["PaymentCallbackController", "PaymentCallbackService", "callback_log"],
  "uncertainties": [
    "No approved ADR was found for the current retry policy."
  ]
}
```

### 6.4 Explanation Policy

回答必须区分：

- Verified facts。
- Human-confirmed experience。
- AI inference。
- Unknowns。

禁止：

- 把 AI inference 写成确定历史事实。
- 没有 source 的“因为当时团队认为”类解释。
- 隐藏冲突知识。

## 7. Knowledge Maintenance Skill

### 7.1 用途

维护 Project Brain 的健康状态。

适用场景：

- commit 后更新知识。
- 清理 stale claims。
- 合并重复 business concept。
- 处理 review queue。

### 7.2 输入

```json
{
  "project_id": "proj_payment",
  "operation": "process_stale_claims",
  "filters": {
    "risk_level": "high",
    "entity_type": "DatabaseTable"
  },
  "max_items": 50
}
```

### 7.3 输出

```json
{
  "skill": "knowledge_maintenance",
  "operation": "process_stale_claims",
  "actions": [
    {
      "type": "create_review_task",
      "claim_id": "claim_...",
      "reason": "Source file changed in commit abc123"
    }
  ],
  "summary": {
    "stale_claims_found": 12,
    "auto_revalidated": 5,
    "review_tasks_created": 7
  }
}
```

## 8. Submit Experience Skill

### 8.1 用途

让人类将经验、禁忌、事故学习录入 ProjectBrain。

### 8.2 输入

```json
{
  "project_id": "proj_payment",
  "statement": "AccountRecord 不允许物理删除，因为涉及财务审计。",
  "claim_type": "HUMAN_CONFIRMED",
  "risk_level": "high",
  "subject": {
    "type": "DatabaseTable",
    "name": "account_record"
  },
  "source": {
    "source_type": "manual_input",
    "author": "tech-lead",
    "note": "Confirmed during architecture review."
  }
}
```

### 8.3 输出

```json
{
  "skill": "submit_experience",
  "claim_id": "claim_...",
  "status": "confirmed",
  "linked_entities": ["db:table:account.account_record"],
  "warnings": []
}
```

## 9. Skill Failure Modes

| Failure | 示例 | 返回策略 |
| --- | --- | --- |
| Project not indexed | 项目未导入 | 返回 `project_not_indexed` 和 ingest 建议 |
| Scope too broad | 用户要求解释整个 monorepo | 返回 partial context 和缩小范围建议 |
| No source | LLM 找不到证据 | 不写入长期记忆，只返回 unknown |
| Conflicting claims | 两条经验冲突 | 返回冲突列表并要求 review |
| Token budget exceeded | context 太大 | 按优先级截断并声明 omitted sections |
| Parser incomplete | Java 动态调用无法静态解析 | 标注 confidence 和 blind spots |

## 10. Skill Output Standard

所有 Skill 输出都应包含：

```json
{
  "skill": "skill_name",
  "project_id": "proj_...",
  "status": "ok",
  "confidence": 0.82,
  "sources": [],
  "warnings": [],
  "omissions": [],
  "generated_at": "2026-06-12T10:00:00Z"
}
```

错误输出：

```json
{
  "skill": "impact_analysis",
  "status": "error",
  "error": {
    "code": "project_not_indexed",
    "message": "Project has no completed ingestion run.",
    "retryable": false
  }
}
```

## 11. Agent Integration Guidance

Coding Agent 使用 ProjectBrain 时推荐顺序：

1. 开始任务前调用 `understand_project` 或 `get_context_pack`。
2. 修改前调用 `impact_analysis`。
3. 遇到架构问题调用 `architecture_explanation`。
4. 完成任务后提交变更摘要给 Brain Update Agent。
5. 如果发现隐性知识，调用 `submit_experience`。

