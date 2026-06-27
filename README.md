<div align="center">
  <img src="docs/logo.svg" width="100" height="100" alt="ProjectBrain Logo"/>
  <h1>ProjectBrain</h1>
  <p>为 AI 编程智能体提供本地项目认知层</p>
  <p>
    <a href="docs/quickstart.md">English Quickstart</a> ·
    <a href="docs/zh/quickstart.md">中文快速上手</a>
  </p>
</div>

---

ProjectBrain 是一个本地项目认知层，帮助 AI 编程智能体在修改代码前理解项目背景。

它将代码结构事实与人工经验转化为任务范围的制品，供 AI 智能体使用：

- **Context Pack**：与当前任务相关的文件、符号、流程、风险和人工注释。
- **Impact Analysis**：某次变更可能影响的文件、符号、调用链、依赖、测试和审查风险。
- **Git Diff Impact**：基于 Git 变更文件的本地变更影响分析。
- **Project Brain**：从 Codex 会话中自动提取知识单元，支持人工确认与检索。

ProjectBrain 不是代码搜索 UI，不是通用 RAG 聊天机器人，也不会自动修改代码。

## 状态

原型 / 本地 MVP。

当前能力：

- CodeGraph SQLite 适配器
- ProjectBrain JSON Schema 模型与校验
- Context Pack 构建器
- Impact Analysis 构建器
- 基于 Git 变更文件的 Git diff 影响分析
- 智能体友好的紧凑输出格式
- 本地经验声明（claim）创作
- JSON 文件本地运行时
- SQLite knowledge store bootstrap
- 本地 stdio MCP 服务器
- Project Brain 知识单元存储与管理
- 可选 FastAPI API 与暗色系 Brain Explorer UI
- 合成公开演示数据 `examples/payment-mini/`

## 快速上手

使用 Homebrew 安装：

```bash
brew tap yinshaojun001/projectbrain https://github.com/yinshaojun001/projectbrain
brew trust yinshaojun001/projectbrain
brew install projectbrain
projectbrain doctor
codex-brain --help
```

或从源码安装：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/projectbrain doctor
```

运行测试：

```bash
python3 -m unittest discover -s tests
```

## 与自己的项目配合使用

一条命令初始化项目：

```bash
projectbrain --store-root ~/.projectbrain-work setup /path/to/my/project \
  --id my_project
```

`setup` 会运行 CodeGraph 索引、导入 ProjectBrain 事实、执行 Context Pack 冒烟测试，并提示安装 MCP 服务器到 Codex CLI、Claude Code、Cursor、Trae 等支持的智能体。

生成 Context Pack：

```bash
projectbrain context my_project "解释结算入口" --format agent
```

生成 Task Understanding Bundle：

```bash
projectbrain understand my_project "解释结算入口"
projectbrain understand my_project "解释结算入口" --format agent
```

启动项目 Intake：

```bash
projectbrain intake project my_project
projectbrain intake answer my_project intake_xxx --answer "这个项目主要负责支付回调和结算处理。"
projectbrain intake answer my_project intake_xxx --answer "主要服务财务结算和支付运营同学。"
```

当前会返回一个最小 intake session，并附带第一条 onboarding 问题。
提交第一问答案后，session 会继续追问“这个项目主要服务谁”，并同步生成一个最小 `Project Baseline Bundle` 草稿。
提交第二问答案后，session 会结束，并把 `primary_users` 写入 baseline 草稿。

生成 Impact Analysis：

```bash
projectbrain impact my_project "修改结算合约" \
  --changed-file src/settlement/SettlementService.java

projectbrain impact-diff my_project "审查暂存变更" --staged --format agent
```

添加人工经验声明：

```bash
projectbrain claim add my_project \
  --id exp_checkout \
  --applies-to checkout \
  --risk high \
  --review-state approved \
  --claim-type HUMAN_CONFIRMED \
  --statement "结账校验变更需要兼容性审查。"
```

## Brain Explorer（知识管理）

启动本地 API 服务后，在浏览器打开：

```
http://127.0.0.1:8000/ui/projects/<project_id>/brain
```

可以：

- 浏览已确认的知识单元（按类型分组）
- 审核待确认的 AI 提取候选知识
- 手动添加知识
- 搜索项目知识库

通过 CLI 管理知识：

```bash
projectbrain brain propose /path/to/my/project --type constraint --statement "退款手续费需单独入账。"
projectbrain brain candidates /path/to/my/project
projectbrain brain confirm-candidate /path/to/my/project <candidate_id>
```

## codex-brain：带项目记忆的 Codex

`codex-brain` 以显式子进程方式启动 Codex CLI，并初始化项目本地 Brain 存储：

```bash
cd /path/to/my/project
codex-brain

# 冒烟测试：
codex-brain --project . --no-ui --no-extract --codex-command "true"
```

项目本地 Brain 数据存储在：

```text
<project>/.projectbrain/brain/
  knowledge_units.jsonl
  memory_candidates.jsonl
  conversations.jsonl
```

## 可选 FastAPI 服务器

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[api]'

PYTHONPATH=apps/api:packages/adapters:packages/runtime:packages/schema \
.venv/bin/uvicorn projectbrain_api.main:app --reload
```

访问 [http://127.0.0.1:8000/ui/projects](http://127.0.0.1:8000/ui/projects) 打开暗色系 Brain Explorer UI。

JSON API 路由：

```text
GET    /health
POST   /api/v1/projects/import
GET    /api/v1/projects
POST   /api/v1/projects/{project_id}/context-pack
POST   /api/v1/projects/{project_id}/impact-analysis
POST   /api/v1/projects/{project_id}/impact-analysis/git-diff
GET    /api/v1/projects/{project_id}/policy
```

## 本地 MCP 服务器

```bash
projectbrain --store-root /absolute/path/to/.projectbrain mcp serve
```

本地 stdio 子进程，不开放网络端口，不上传源码。详见 [MCP 使用说明](docs/mcp-usage.md)。

在 MCP 工具调用中使用 `output_format: "agent"` 获取紧凑的智能体友好输出。

本地输出控制，在项目根目录添加 `.projectbrain-policy.json`：

```json
{
  "deny_paths": ["private/**"],
  "output_limits": { "max_items_per_section": 8 },
  "include_source_snippets": false
}
```

## 仓库结构

```text
apps/
  api/projectbrain_api/   可选 FastAPI API 与 UI
packages/
  adapters/               CodeGraph 适配器与制品构建器
  runtime/                本地 JSON 运行时与仓库抽象
  schema/                 数据类 Schema 与校验
examples/payment-mini/    合成公开演示数据
tests/                    单元与 API 测试
docs/                     设计与实现文档
```

## 设计文档

| 文档 | 说明 |
| --- | --- |
| [设计文档](docs/projectbrain/design-document.md) | 产品定位、架构、组件、API 与路线图 |
| [域模型](docs/projectbrain/domain-model.md) | 项目认知域模型与界限上下文 |
| [MVP 架构](docs/projectbrain/mvp-architecture.md) | 本地 MVP 架构、服务边界与验收标准 |
| [MCP 使用说明](docs/mcp-usage.md) | 本地 stdio MCP 服务器使用与隐私边界 |
| [中文快速上手](docs/zh/quickstart.md) | 本地安装、演示、MCP、声明与策略的中文教程 |

## 路线图

- 增加类型化 API 请求/响应模型
- 增加 OpenAPI 快照测试
- 增加更丰富的 Git diff 符号匹配
- 增加数据库后端仓库实现
- 增加更多语言适配器

## 许可证

MIT
