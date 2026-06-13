# ProjectBrain API Contract

| Field | Value |
| --- | --- |
| Document | API Contract |
| Project | ProjectBrain |
| Status | Draft |
| Last updated | 2026-06-12 |

## 1. API 设计目标

ProjectBrain API 服务三类调用方：

1. Web Console。
2. Brain Update Worker / Agent。
3. 外部 Coding Agent 和 MCP Server。

API 必须保证：

- 返回内容可追溯 source。
- 长任务异步执行。
- 知识写入经过 confidence、source、review gate。
- Agent 可以请求 task-scoped context pack。
- 大型项目中 API 不返回无边界全量图。

## 2. Common Types

### 2.1 EntityRef

```json
{
  "id": "ent_...",
  "stable_key": "java:class:payment-service:com.acme.payment.RefundService",
  "entity_type": "Class",
  "name": "RefundService",
  "qualified_name": "com.acme.payment.RefundService"
}
```

### 2.2 SourceRef

```json
{
  "id": "src_...",
  "source_type": "code_location",
  "uri": "git://payment-platform@abc123/payment-service/src/main/java/.../RefundService.java",
  "locator": {
    "file": "payment-service/src/main/java/com/acme/payment/RefundService.java",
    "start_line": 42,
    "end_line": 68,
    "symbol": "RefundService.createRefund"
  }
}
```

### 2.3 KnowledgeClaim

```json
{
  "id": "claim_...",
  "claim_type": "AI_INFERENCE",
  "subject": {
    "stable_key": "java:class:payment-service:com.acme.payment.RefundService"
  },
  "predicate": "IMPLEMENTS",
  "object": {
    "stable_key": "concept:refund"
  },
  "statement": "RefundService implements refund orchestration.",
  "confidence": 0.76,
  "lifecycle_state": "active",
  "review_state": "pending",
  "risk_level": "normal",
  "sources": []
}
```

### 2.4 Error

```json
{
  "error": {
    "code": "validation_error",
    "message": "claim source is required",
    "details": {},
    "retryable": false
  }
}
```

## 3. Project APIs

### 3.1 Create Project

`POST /api/v1/projects`

Request:

```json
{
  "name": "payment-platform",
  "repository_url": "https://github.com/acme/payment-platform",
  "default_branch": "main",
  "description": "Payment and refund platform"
}
```

Response:

```json
{
  "id": "proj_...",
  "name": "payment-platform",
  "repository_url": "https://github.com/acme/payment-platform",
  "default_branch": "main",
  "status": "created",
  "created_at": "2026-06-12T10:00:00Z"
}
```

### 3.2 Get Project

`GET /api/v1/projects/{project_id}`

Response:

```json
{
  "id": "proj_...",
  "name": "payment-platform",
  "primary_languages": ["Java", "SQL"],
  "last_indexed_at": "2026-06-12T10:00:00Z",
  "statistics": {
    "entities": 12034,
    "relations": 48502,
    "claims": 904,
    "active_constraints": 31
  }
}
```

## 4. Ingestion APIs

### 4.1 Start Ingestion

`POST /api/v1/projects/{project_id}/ingestions`

Request:

```json
{
  "source": {
    "type": "git_repository",
    "ref": "main"
  },
  "options": {
    "include_git_history": false,
    "include_docs": true,
    "max_files": 20000,
    "languages": ["java", "sql", "markdown"]
  }
}
```

Response:

```json
{
  "brain_run_id": "run_...",
  "status": "queued"
}
```

### 4.2 Get BrainRun

`GET /api/v1/projects/{project_id}/runs/{run_id}`

Response:

```json
{
  "id": "run_...",
  "run_type": "initial_ingestion",
  "status": "completed",
  "started_at": "2026-06-12T10:00:00Z",
  "completed_at": "2026-06-12T10:04:12Z",
  "output": {
    "files_scanned": 4821,
    "entities_created": 12034,
    "relations_created": 48502,
    "claims_created": 126,
    "review_tasks_created": 14
  }
}
```

## 5. Context Pack APIs

### 5.1 Generate Context Pack

`POST /api/v1/projects/{project_id}/context-pack`

Request:

```json
{
  "task": "Add refund handling fee",
  "files": [
    "payment-service/src/main/java/com/acme/payment/RefundService.java"
  ],
  "symbols": ["RefundService.createRefund"],
  "business_concepts": ["Refund"],
  "max_tokens": 8000,
  "include": ["facts", "constraints", "flows", "decisions", "tests"]
}
```

Response:

```json
{
  "context_pack_id": "ctx_...",
  "project_id": "proj_...",
  "summary": "The task touches refund creation, fee calculation, and accounting record generation.",
  "sections": [
    {
      "type": "critical_constraints",
      "items": [
        {
          "statement": "AccountRecord must not be physically deleted because it is used for financial audit.",
          "confidence": 1.0,
          "sources": [
            {
              "id": "src_adr_0042",
              "source_type": "adr"
            }
          ]
        }
      ]
    }
  ],
  "recommended_files": [],
  "recommended_tests": [],
  "warnings": [],
  "omissions": []
}
```

## 6. Impact Analysis APIs

### 6.1 Analyze Impact

`POST /api/v1/projects/{project_id}/impact-analysis`

Request:

```json
{
  "change": {
    "type": "diff",
    "content": "diff --git ..."
  },
  "depth": 4,
  "include": ["code", "data", "api", "message", "business", "constraints", "tests"]
}
```

Response:

```json
{
  "analysis_id": "impact_...",
  "summary": "The change likely affects refund amount calculation and accounting records.",
  "changed_entities": [],
  "affected_entities": [],
  "affected_business_concepts": [],
  "affected_tables": [],
  "affected_apis": [],
  "affected_topics": [],
  "critical_constraints": [],
  "related_decisions": [],
  "related_incidents": [],
  "recommended_tests": [],
  "confidence": 0.82,
  "warnings": []
}
```

## 7. Knowledge Query APIs

### 7.1 Search Entities

`GET /api/v1/projects/{project_id}/entities?query=RefundService&type=Class`

Response:

```json
{
  "items": [
    {
      "id": "ent_...",
      "stable_key": "java:class:payment-service:com.acme.payment.RefundService",
      "entity_type": "Class",
      "name": "RefundService",
      "qualified_name": "com.acme.payment.RefundService"
    }
  ]
}
```

### 7.2 Get Entity Neighborhood

`GET /api/v1/projects/{project_id}/entities/{entity_id}/neighborhood?depth=2`

Response:

```json
{
  "root": {},
  "nodes": [],
  "edges": []
}
```

### 7.3 Query Claims

`POST /api/v1/projects/{project_id}/claims/query`

Request:

```json
{
  "subject_stable_key": "db:table:account.account_record",
  "claim_types": ["HUMAN_CONFIRMED", "POLICY"],
  "lifecycle_states": ["active", "confirmed"],
  "include_sources": true
}
```

Response:

```json
{
  "items": []
}
```

## 8. Knowledge Write APIs

### 8.1 Create Claim

`POST /api/v1/projects/{project_id}/claims`

Request:

```json
{
  "claim_type": "HUMAN_CONFIRMED",
  "subject": {
    "stable_key": "db:table:account.account_record"
  },
  "predicate": "HAS_CONSTRAINT",
  "statement": "AccountRecord 不允许物理删除，因为涉及财务审计。",
  "confidence": 1.0,
  "risk_level": "high",
  "sources": [
    {
      "source_type": "manual_input",
      "quote": "AccountRecord 不允许物理删除，因为涉及财务审计。"
    }
  ]
}
```

Response:

```json
{
  "id": "claim_...",
  "lifecycle_state": "confirmed",
  "review_state": "approved",
  "created_at": "2026-06-12T10:00:00Z"
}
```

### 8.2 Review Claim

`PATCH /api/v1/projects/{project_id}/claims/{claim_id}/review`

Request:

```json
{
  "decision": "approve",
  "reason": "Confirmed by payment platform tech lead.",
  "reviewer": "alice"
}
```

Response:

```json
{
  "id": "claim_...",
  "lifecycle_state": "confirmed",
  "review_state": "approved"
}
```

## 9. Git Event APIs

### 9.1 Git Webhook

`POST /api/v1/projects/{project_id}/events/git`

Request:

```json
{
  "event_type": "commit",
  "repository": "payment-platform",
  "branch": "main",
  "commit_sha": "abc123",
  "message": "增加退款手续费",
  "author": "dev@example.com",
  "changed_files": [
    {
      "path": "payment-service/src/main/java/com/acme/payment/RefundFeeCalculator.java",
      "change_type": "modified"
    }
  ]
}
```

Response:

```json
{
  "brain_run_id": "run_...",
  "status": "queued"
}
```

## 10. Review APIs

### 10.1 List Review Tasks

`GET /api/v1/projects/{project_id}/review-tasks?status=open`

Response:

```json
{
  "items": [
    {
      "id": "review_...",
      "task_type": "validate_ai_inference",
      "priority": "high",
      "title": "Confirm refund handling fee business concept",
      "claim_id": "claim_...",
      "created_at": "2026-06-12T10:00:00Z"
    }
  ]
}
```

### 10.2 Resolve Review Task

`PATCH /api/v1/projects/{project_id}/review-tasks/{task_id}`

Request:

```json
{
  "decision": "approved",
  "reason": "Matches current refund design.",
  "reviewer": "alice"
}
```

Response:

```json
{
  "id": "review_...",
  "status": "resolved",
  "resolved_at": "2026-06-12T10:00:00Z"
}
```

## 11. MCP Tool Contracts

### 11.1 `projectbrain_understand_project`

Input:

```json
{
  "project_id": "proj_...",
  "scope": {
    "modules": ["payment-service"]
  },
  "max_tokens": 8000
}
```

Output:

```json
{
  "summary": "...",
  "module_map": [],
  "business_concepts": [],
  "critical_constraints": [],
  "recommended_entrypoints": []
}
```

### 11.2 `projectbrain_get_context_pack`

Input:

```json
{
  "project_id": "proj_...",
  "task": "Add refund handling fee",
  "files": [],
  "symbols": [],
  "max_tokens": 8000
}
```

Output:

```json
{
  "context_pack_id": "ctx_...",
  "summary": "...",
  "sections": [],
  "warnings": []
}
```

### 11.3 `projectbrain_analyze_impact`

Input:

```json
{
  "project_id": "proj_...",
  "diff": "diff --git ...",
  "depth": 4
}
```

Output:

```json
{
  "summary": "...",
  "affected_entities": [],
  "critical_constraints": [],
  "recommended_tests": []
}
```

### 11.4 `projectbrain_submit_memory`

Input:

```json
{
  "project_id": "proj_...",
  "statement": "AccountRecord 不允许物理删除，因为涉及财务审计。",
  "subject": {
    "stable_key": "db:table:account.account_record"
  },
  "risk_level": "high"
}
```

Output:

```json
{
  "claim_id": "claim_...",
  "status": "confirmed"
}
```

## 12. API Error Codes

| Code | HTTP | Meaning |
| --- | --- | --- |
| `project_not_found` | 404 | Project 不存在 |
| `project_not_indexed` | 409 | Project 尚未完成导入 |
| `invalid_source` | 400 | claim 缺少合法 source |
| `confidence_gate_failed` | 422 | 置信度不足，不能 active |
| `review_required` | 202 | 已创建审核任务 |
| `entity_not_found` | 404 | 实体不存在 |
| `run_not_found` | 404 | BrainRun 不存在 |
| `token_budget_exceeded` | 200 | 非错误，返回 omissions |
| `unsupported_language` | 422 | 当前 parser 不支持 |
| `parser_failed` | 500 | parser 内部错误 |

## 13. Pagination and Limits

默认：

- list API `limit=50`。
- 最大 `limit=500`。
- context pack 默认 `max_tokens=8000`。
- impact analysis 默认 `depth=3`。
- 单次 diff 最大 2 MB，超过后要求通过 artifact reference 传入。

## 14. Idempotency

以下 API 应支持 idempotency key：

- create project。
- start ingestion。
- git webhook。
- create claim。
- review task resolve。

Header:

```text
Idempotency-Key: 01J...
```

## 15. Versioning

API 使用 path version：

```text
/api/v1/...
```

破坏性变更进入 `/api/v2`。非破坏性新增字段允许在 V1 内演进。

