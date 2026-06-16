# Phase 6 — Human Observability UI

## 1. 目标与非目标

### 目标
为 ProjectBrain 增加一个本地 Web 面板，让**人类维护者**能够：

1. 看到 AI agent 通过 MCP / API 拿到的 Context Pack 和 Impact Analysis 长什么样。
2. 审阅与录入 Experience Claims（人类经验一等公民）。
3. 预览 staged / branch / last-commit 的 Git diff impact，验证策略与裁剪是否生效。
4. 检查 `.projectbrain-policy` 当前的有效配置。

### 非目标（关键约束，遵循 [STATE.md L11](file:///Users/a58/personal/codeunderstand/.planning/STATE.md#L11)）

- ❌ 不做"代码搜索 UI / 通用代码图浏览器"。
- ❌ 不做"自动改代码"的交互入口。
- ❌ 不引入数据库、不改变本地 JSON 运行时。
- ❌ 不暴露公网；仅 `127.0.0.1` 本机绑定。
- ✅ UI 是 agent workflow 的**可观测层**，不是主产品。

---

## 2. 技术方案选型

### 选型对比

| 方案 | 工作量 | 与路线图一致性 | 部署复杂度 | 维护成本 |
|---|---|---|---|---|
| A. React SPA + Vite | 高（5-7 天） | ✅ 完全一致（路线图既定 React） | 需 Node 工具链 | 中 |
| **B. FastAPI + Jinja2 + HTMX** | **低（2-3 天）** | ⚠️ 与路线图最终态有差距 | 零额外工具链 | 低 |
| C. Streamlit | 极低（1 天） | ❌ 偏离路线图，样式弱 | 需新依赖 | 低但不可演进 |

### 推荐：**方案 B（FastAPI + Jinja2 + HTMX）**

**理由：**
1. **匹配"观测工具"定位**：项目明确不做 dashboard-first 产品，UI 不应抢戏，HTMX 的轻量服务端渲染最合适。
2. **零工具链增量**：复用现有 FastAPI 进程和 Python 环境，无 Node / 无构建步骤，符合 `brew install` 单命令安装的产品形态。
3. **隐私边界清晰**：所有渲染都在本地 Python 进程内完成，不引入 CORS 复杂度，不引入第三方 CDN。
4. **可演进**：API 层保持纯 JSON，未来如果团队决定上 React SPA，HTMX 模板可以丢弃，API 直接复用。

**新增依赖**（写入 `pyproject.toml` 的 `[api]` extra）：
```toml
api = ["fastapi>=0.115", "uvicorn>=0.30", "httpx>=0.28", "jinja2>=3.1", "python-multipart>=0.0.9"]
```
HTMX 通过 CDN 或本地静态文件引入，无 Python 依赖。

---

## 3. P0 范围 — 最小页面清单

所有页面挂在 `/ui/*` 路径下，与 `/api/v1/*` 隔离。

### P0-1 项目列表页 `GET /ui/projects`
- 表格：project_id、name、source_path、imported_at、experience_claims 数量。
- 行操作：进入 Context Pack / 进入 Impact Analysis / 进入 Claims / 查看 Policy。
- 顶部"导入新项目"表单（HTMX `hx-post` 到 `/api/v1/projects/import`）。
- 数据来源：[`list_projects_handler`](file:///Users/a58/personal/codeunderstand/apps/api/projectbrain_api/handlers.py#L32-L33)。

### P0-2 Context Pack 浏览器 `GET /ui/projects/{id}/context`
- 顶部任务输入框：`task` 文本框 + `max_items_per_section` 数字框 + 提交按钮。
- 提交 HTMX `hx-post` 到 `/api/v1/projects/{id}/context-pack`，结果区局部刷新。
- 分块展示：
  - **Files**（文件路径表）
  - **Symbols**（kind / name / file 表）
  - **Flows**（调用流图，纯 ASCII / mermaid）
  - **Risks**（风险条目）
  - **Experience Claims**（适用此任务的人类经验）
- "保存为 fixture"按钮：把 JSON 落到 `.projectbrain/fixtures/` 用作回归基线。
- 数据来源：[`build_context_pack`](file:///Users/a58/personal/codeunderstand/packages/runtime/projectbrain_runtime/service.py#L73-L93)。

### P0-3 Impact Analysis 视图 `GET /ui/projects/{id}/impact`
- 任务输入框 + Tab 切换三种触发方式：
  - **Tab 1 — 手动列文件**：`changed_files` 多行输入 + `changed_symbols`。
  - **Tab 2 — Git diff**：选择 `--staged` / `--branch from..to` / `--last-commit`，调 `analyze_git_diff_impact`。
  - **Tab 3 — Last run**：直接读 `.projectbrain/runs/<project_id>/impact-analysis-latest.json` 不重算。
- 结果区分块：受影响 callers / dependencies / tests / review risks，每条带 file 路径锚点。
- "导出 agent compact 格式"按钮：调 `output_format=agent` 生成精简版。
- 数据来源：[`analyze_impact`](file:///Users/a58/personal/codeunderstand/packages/runtime/projectbrain_runtime/service.py#L95-L119) 与 [`analyze_git_diff_impact`](file:///Users/a58/personal/codeunderstand/packages/runtime/projectbrain_runtime/service.py#L121-L144)。

### P0 不做（推到 P1+）
- Claims 的可视化编辑器（P0 仅做只读列表，编辑走 CLI/API）。
- Knowledge Graph 关系图可视化。
- 多用户、登录态。
- 主题切换、深色模式。

---

## 4. 后端 API 缺口补齐

运行时方法**全部存在**，缺的只是 HTTP 包装。在 [`apps/api/projectbrain_api/main.py`](file:///Users/a58/personal/codeunderstand/apps/api/projectbrain_api/main.py) 增加：

### 4.1 Claims 端点

```text
GET    /api/v1/projects/{id}/claims                  # list (?include_archived=true)
POST   /api/v1/projects/{id}/claims                  # add
PATCH  /api/v1/projects/{id}/claims/{claim_id}       # review / 更新
DELETE /api/v1/projects/{id}/claims/{claim_id}       # archive (soft delete, 带 reason)
```

直接包装 [`add_experience_claim`](file:///Users/a58/personal/codeunderstand/packages/runtime/projectbrain_runtime/service.py#L154-L186) / `list_experience_claims` / `review_experience_claim` / `archive_experience_claim`。

对应 handler 写入 [`handlers.py`](file:///Users/a58/personal/codeunderstand/apps/api/projectbrain_api/handlers.py)，遵循现有 `_require_payload_keys` 风格。

### 4.2 Git diff Impact 端点

```text
POST /api/v1/projects/{id}/impact-analysis/git-diff
```

请求体：
```json
{
  "task": "Review staged changes",
  "selection": { "kind": "staged" }                  // 或 {"kind":"branch","from":"main","to":"HEAD"} / {"kind":"last-commit"}
}
```

包装 [`analyze_git_diff_impact`](file:///Users/a58/personal/codeunderstand/packages/runtime/projectbrain_runtime/service.py#L121-L144)，复用 `GitDiffSelection`。

### 4.3 Policy 端点

```text
GET /api/v1/projects/{id}/policy
```

包装 [`inspect_policy`](file:///Users/a58/personal/codeunderstand/packages/runtime/projectbrain_runtime/service.py#L146-L152)。供 UI 在每个项目页右上角显示"当前生效的 deny_paths / output_limits"摘要。

### 4.4 CORS

**P0 不需要 CORS**。HTMX 与 FastAPI 同源（`127.0.0.1:8000`）。

仅当未来切到方案 A（React SPA 独立端口）时，再加 `fastapi.middleware.cors.CORSMiddleware`，且白名单只允许 `http://127.0.0.1:5173` 等本地端口。生产环境永远不开放公网 origin。

### 4.5 SSE 进度反馈

**P0 不做完整 SSE**，但需要解决长任务卡死前端的问题：

| 任务 | P0 处理 | P1 升级 |
|---|---|---|
| 项目导入（CodeGraph 索引） | 同步等待 + HTMX `hx-indicator` 转圈 | SSE 推送阶段进度（init/index/import/smoke） |
| Context Pack 构建 | 通常 < 1s，同步即可 | 无需升级 |
| Impact Analysis | 通常 < 2s，同步即可 | 无需升级 |
| Git diff impact | git 调用 + 计算，同步即可 | 无需升级 |

**P1 SSE 设计草案（仅为 import）**：
- 端点：`GET /api/v1/projects/{id}/import/stream?token=...`
- 事件类型：`stage`（init/index/import/smoke/done）+ `error`。
- 实现：`StreamingResponse` + `asyncio.Queue`，运行时层加可选 `progress_callback`。

---

## 5. 任务分解

按依赖顺序分 4 个 wave，建议两人天内完成 P0。

### Wave 1 — 后端 API 缺口（先做，UI 才有数据消费）
- [ ] **T1.1** 在 `handlers.py` 新增 4 个 claims handler + git-diff-impact handler + policy handler。
- [ ] **T1.2** 在 `main.py` 注册 6 个新路由，统一异常映射到 HTTPException。
- [ ] **T1.3** 在 `tests/test_api_handlers.py` 与 `test_api_fastapi.py` 增加新端点的单元 + 集成测试。
- [ ] **T1.4** 在 `docs/projectbrain/api-contract.md` 补充新端点契约。

### Wave 2 — UI 脚手架
- [ ] **T2.1** `pyproject.toml` 的 `[api]` extra 加 `jinja2`、`python-multipart`。
- [ ] **T2.2** 新建目录：
  ```text
  apps/api/projectbrain_api/
    ui/
      __init__.py
      router.py            # /ui/* 路由
      templates/
        base.html          # 顶部导航 + HTMX CDN
        projects/list.html
        projects/context.html
        projects/impact.html
        projects/policy.html
        _partials/         # HTMX 局部刷新片段
      static/
        app.css            # 单文件极简样式（不引 Tailwind）
  ```
- [ ] **T2.3** 在 `main.py` 用 `app.include_router(ui_router)` 挂载，`StaticFiles` 挂 `/ui/static`。
- [ ] **T2.4** `base.html` 引入 HTMX（推荐固定版本本地静态文件，避免 CDN 依赖）。

### Wave 3 — P0 三个页面
- [ ] **T3.1** 项目列表页 + 导入表单（HTMX 提交后局部刷新表格）。
- [ ] **T3.2** Context Pack 浏览器（任务输入 → 局部刷新结果分块）。
- [ ] **T3.3** Impact Analysis 视图（三个 Tab：手动 / Git diff / Last run）。
- [ ] **T3.4** Policy 摘要侧边栏（每个项目页右上角）。

### Wave 4 — 验收与文档
- [ ] **T4.1** 添加 `tests/test_ui_smoke.py`：用 `httpx.AsyncClient` 验证每个 `/ui/*` 页面返回 200 且包含关键元素。
- [ ] **T4.2** 更新 [`README.md`](file:///Users/a58/personal/codeunderstand/README.md)「Optional FastAPI Server」一节，说明 `--reload` 后访问 `http://127.0.0.1:8000/ui/projects`。
- [ ] **T4.3** 更新 [`STATE.md`](file:///Users/a58/personal/codeunderstand/.planning/STATE.md)，记录 Phase 6 完成状态。
- [ ] **T4.4** 更新 `docs/release-readiness.md`，补一条"UI 冒烟测试"项。

---

## 6. 验收标准（goal-backward）

UI 上线后，下面每条都必须为真才算 P0 完成：

1. ✅ 在公开 demo `examples/payment-mini/` 上，能完整跑通：导入 → 看 Context Pack → 看 Impact Analysis → 看 Git diff impact（用本仓库的 staged 变更模拟）。
2. ✅ 在已导入的真实私有项目（如 `docs/payment/huangye_scf_hysjpaymentplatform/`）上，UI 看到的内容与 CLI `projectbrain context / impact / impact-diff` 一致。
3. ✅ Policy 的 `deny_paths` 在 UI 输出中生效（路径不出现在结果列表里）。
4. ✅ `python -m unittest discover -s tests` 全绿，新加测试覆盖 API 缺口与 UI 冒烟。
5. ✅ `uvicorn` 进程仅绑定 `127.0.0.1`，`netstat` 验证不监听 `0.0.0.0`。
6. ✅ README 的快速上手段落新增的 UI 章节，新人按步骤能在 5 分钟内打开第一个页面。

---

## 7. 风险与回滚

| 风险 | 应对 |
|---|---|
| HTMX 版本漂移导致页面坏 | 静态托管固定版本，不走 CDN |
| Jinja2 模板里误渲染源码片段，泄露私有内容 | 复用现有 `apply_output_policy`，UI 层不绕过 policy |
| UI 让用户误以为 ProjectBrain 是"代码浏览器" | README 与每个页面顶部加 banner："This UI is for observing AI agent context, not for code search" |
| import 长任务卡前端 | P0 用 `hx-indicator`；P1 升级 SSE |
| 回滚 | UI 全部代码隔离在 `apps/api/projectbrain_api/ui/` 与新增路由文件中；删除该目录 + 回滚 `main.py`、`pyproject.toml` 即可完全移除 |

---

## 8. 时间预估

| Wave | 工作量 | 依赖 |
|---|---|---|
| Wave 1 后端 API | 0.5 - 1 天 | 无 |
| Wave 2 UI 脚手架 | 0.5 天 | Wave 1 |
| Wave 3 P0 三页面 | 1 - 1.5 天 | Wave 2 |
| Wave 4 验收文档 | 0.5 天 | Wave 3 |
| **总计 P0** | **2.5 - 3.5 人日** | — |

---

## 9. 后续路线图（不在 P0 内）

- **P1**：Claims 可视化编辑、SSE import 进度、agent compact 输出对比视图。
- **P2**：Knowledge graph mermaid 渲染、跨项目搜索、Run history 时间轴。
- **P3**：（仅当团队决定）切换到 React SPA 方案 A，把 HTMX 模板替换为 SPA，API 不动。
