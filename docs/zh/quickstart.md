# ProjectBrain 中文快速上手

ProjectBrain 是一个本地优先的项目认知层，面向 AI coding agent。

它把代码结构事实和人工项目经验整理成 agent 在改代码前可以读取的结构化上下文：

- **Context Pack**：与任务相关的文件、符号、调用关系、风险和人工经验。
- **Impact Analysis**：一次改动可能影响的文件、符号、调用方、依赖、测试和人工 review 风险。
- **Git Diff Impact**：基于本地 Git changed file names，对 staged、分支范围或最近提交做影响分析。
- **Experience Claims**：本地记录和治理人工项目经验。
- **Privacy Policy**：通过本地 `.projectbrain-policy` 控制输出范围。

ProjectBrain 不是代码搜索 UI、通用 RAG 聊天机器人，也不会自动改代码。

## 1. 本地安装

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

检查 CLI：

```bash
.venv/bin/projectbrain doctor
```

期望输出形状：

```json
{
  "status": "ok",
  "python": "3.x.x",
  "store_root": ".projectbrain"
}
```

运行测试：

```bash
.venv/bin/python -m unittest discover -s tests
```

## 2. 使用公开合成 Demo

仓库内置的 `examples/payment-mini/` 是合成数据，不包含真实私有代码。

生成 Context Pack：

```bash
.venv/bin/projectbrain facts context \
  --export-json examples/payment-mini/projectbrain-codegraph-export.json \
  --experience-seed examples/payment-mini/experience-seed.md \
  --task "Explain the settlement entrypoint"
```

生成 Impact Analysis：

```bash
.venv/bin/projectbrain facts impact \
  --export-json examples/payment-mini/projectbrain-codegraph-export.json \
  --experience-seed examples/payment-mini/experience-seed.md \
  --task "Change the settlement contract" \
  --changed-file contract/src/main/java/example/payment/settlement/SettlementService.java
```

## 3. 导入自己的项目

ProjectBrain 当前从 CodeGraph SQLite 数据库读取代码事实，默认路径是：

```text
<your-project>/.codegraph/codegraph.db
```

导入一个受限范围：

```bash
.venv/bin/projectbrain import /path/to/your/project \
  --id my_project \
  --name "My Project" \
  --path-prefix src/ \
  --kind class \
  --kind interface \
  --kind method
```

导入后，ProjectBrain 会把运行时数据写入 `.projectbrain/`。这个目录应该保持本地私有，不要提交到 Git。

## 4. 生成任务上下文

```bash
.venv/bin/projectbrain context my_project "Explain the checkout flow"
```

如果输出给 AI coding agent 使用，可以选择紧凑格式：

```bash
.venv/bin/projectbrain context my_project "Explain the checkout flow" --format agent
```

`agent` 格式保留最可执行的信息，例如 summary、must-read files、risk warnings、recommended tests 和 manual-review guidance。

## 5. 分析改动影响

显式指定 changed file：

```bash
.venv/bin/projectbrain impact my_project "Change checkout validation" \
  --changed-file src/checkout/CheckoutService.java
```

分析当前 staged diff：

```bash
.venv/bin/projectbrain impact-diff my_project "Review staged checkout changes" --staged
```

分析分支或 ref 范围：

```bash
.venv/bin/projectbrain impact-diff my_project "Review branch impact" --from main --to HEAD
```

`impact-diff` 只从本地 Git 读取 changed file names，然后映射到已导入的 ProjectBrain facts。它不会读取或返回源文件正文。

## 6. 添加和治理项目经验

添加本地经验 claim：

```bash
.venv/bin/projectbrain claim add my_project \
  --id exp_checkout_validation \
  --applies-to checkout \
  --risk high \
  --review-state approved \
  --claim-type HUMAN_CONFIRMED \
  --statement "Checkout validation changes require compatibility review."
```

列出 claim：

```bash
.venv/bin/projectbrain claim list my_project
```

更新 review 状态：

```bash
.venv/bin/projectbrain claim review my_project exp_checkout_validation \
  --review-state needs_review \
  --risk medium
```

归档 claim：

```bash
.venv/bin/projectbrain claim archive my_project exp_checkout_validation \
  --reason "Superseded by newer checkout guidance."
```

查看包含归档项的完整列表：

```bash
.venv/bin/projectbrain claim list my_project --include-archived
```

归档的 claim 会继续保存在本地 `experience_claims.json` 中，但 Context Pack 和 Impact Analysis 会忽略它们。

## 7. 本地隐私策略

在被导入项目根目录添加 `.projectbrain-policy.json`，可以控制 ProjectBrain 输出：

```json
{
  "deny_paths": ["private/**", "src/main/resources/config/**"],
  "output_limits": {
    "max_items_per_section": 8,
    "max_recommended_files": 8,
    "max_recommended_tests": 5
  },
  "include_source_snippets": false
}
```

支持的策略文件名：

```text
.projectbrain-policy.json
.projectbrain-policy.yml
.projectbrain-policy.yaml
```

检查当前项目加载到的策略：

```bash
.venv/bin/projectbrain policy inspect my_project
```

策略会应用到 Context Pack、Impact Analysis、Git diff review、API 和 MCP 返回的读输出。默认情况下，`body`、`snippet`、`source_code` 等 source-like 字段会被移除。

## 8. 本地 MCP Server

启动本地 stdio MCP server：

```bash
.venv/bin/projectbrain --store-root /absolute/path/to/.projectbrain mcp serve
```

MCP server 是本地子进程：

- 不打开网络 socket。
- 不上传源码。
- 不调用 hosted ProjectBrain 服务。
- 通过 stdin/stdout 和 MCP client 通信。

当前主要 MCP tools：

```text
projectbrain_import_project
projectbrain_list_projects
projectbrain_inspect_policy
projectbrain_add_experience_claim
projectbrain_list_experience_claims
projectbrain_review_experience_claim
projectbrain_archive_experience_claim
projectbrain_context_pack
projectbrain_impact_analysis
projectbrain_review_git_diff
```

检查 MCP tool list：

```bash
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n' | .venv/bin/projectbrain mcp serve
```

## 9. 隐私边界

ProjectBrain 控制的是工具侧隐私边界。它本身不上传代码，也不会启动远程服务。

但 MCP tool result 会返回给你的 AI coding client。结果可能包含：

- 本地路径
- 符号名
- 调用关系
- inferred business concepts
- risk notes

这些内容是否会进入模型 provider，取决于你的 AI client、模型和账号设置。严格私有代码环境建议使用本地模型或企业批准的模型端点。

不要提交这些本地或私有材料：

- `docs/payment/`
- `.projectbrain/`
- 私有代码生成的 `.codegraph/`
- 私有 experience seed
- 私有 exported facts
- `docs/next-conversation.md`

## 10. v0.2 发布前检查

发布或对外推荐前，至少运行：

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/projectbrain doctor
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n' | .venv/bin/projectbrain mcp serve
```

还需要确认：

- GitHub Actions 通过。
- 没有提交私有源码、`.projectbrain/` 或私有 `.codegraph/`。
- README、quickstart、MCP usage 和 privacy policy 文档与实际 CLI 行为一致。

完整检查清单见 [v0.2 Release Readiness](../release-readiness.md)。
