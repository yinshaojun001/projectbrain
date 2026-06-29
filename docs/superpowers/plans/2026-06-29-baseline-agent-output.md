# Baseline Agent Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `projectbrain baseline show` 和 `projectbrain baseline build` 增加 `--format agent`，让项目基线可以直接作为 AI 编程智能体的稳定输入物。

**Architecture:** 保持现有 Baseline 持久化结构与 runtime 行为不变，只在统一输出投影层新增 Project Baseline 的 Agent 视图，并把 `baseline` CLI 子命令接入现有 `format_output()`。测试先从纯 formatter 单测起步，再补 CLI 红绿，最后更新文档并跑回归。

**Tech Stack:** Python 3.11, argparse CLI, unittest

---

## File Structure

**Modify**
- `packages/runtime/projectbrain_runtime/agent_output.py`
  - 负责把 `{ "baseline": ... }` 投影成稳定的 `agent_output`
- `packages/runtime/projectbrain_cli/main.py`
  - 负责给 `baseline build/show` 注册 `--format` 并走统一 formatter
- `tests/test_cli.py`
  - 负责验证 CLI 新增的 Agent 输出行为
- `README.md`
  - 负责公开用法说明
- `docs/projectbrain/local-runtime.md`
  - 负责本地运行时命令说明

**Create**
- `tests/test_agent_output.py`
  - 负责给 `agent_output.py` 增加最小、独立、快速的单测

**Responsibility boundaries**
- `agent_output.py` 只做输出投影，不参与 Baseline 构建或存储
- `main.py` 只做 CLI 参数注册与分发，不手写 Baseline Agent 字段结构
- `tests/test_agent_output.py` 只验证纯格式化逻辑
- `tests/test_cli.py` 只验证命令入口和集成行为

---

### Task 1: `feat/v1-32-baseline-agent-formatter`

**Files:**
- Create: `tests/test_agent_output.py`
- Modify: `packages/runtime/projectbrain_runtime/agent_output.py`

- [ ] **Step 1: Write the failing formatter test**

```python
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "runtime"))

from projectbrain_runtime.agent_output import format_output  # noqa: E402


class ProjectBaselineAgentOutputTest(unittest.TestCase):
    def test_format_output_returns_project_baseline_agent_view(self):
        output = format_output(
            {
                "baseline": {
                    "bundle_type": "project_baseline",
                    "project_id": "payment_demo",
                    "project_summary": "支付项目基线",
                    "project_goal": "负责支付回调和结算处理。",
                    "primary_users": [{"name": "财务"}],
                    "core_modules": [{"name": "settlement"}],
                    "key_flows": [{"name": "callback"}],
                    "third_party_integrations": [{"name": "bank"}],
                    "high_risk_areas": [{"name": "idempotency"}],
                    "constraints": [{"name": "不可重复结算"}],
                    "validation_strategy": [{"name": "回调集成测试"}],
                    "priority_evidence": [{"name": "支付文档"}],
                    "unknowns": [{"name": "退款边界"}],
                    "quality_notes": [{"name": "需人工确认"}],
                }
            },
            "agent",
        )

        self.assertEqual(output["agent_output"]["artifact_type"], "project_baseline")
        self.assertEqual(output["agent_output"]["project_id"], "payment_demo")
        self.assertEqual(output["agent_output"]["project_goal"], "负责支付回调和结算处理。")
        self.assertEqual(output["agent_output"]["primary_users"], [{"name": "财务"}])
        self.assertEqual(output["agent_output"]["quality_notes"], [{"name": "需人工确认"}])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3.11 -m unittest tests.test_agent_output.ProjectBaselineAgentOutputTest.test_format_output_returns_project_baseline_agent_view -v
```

Expected: FAIL，因为当前 `format_agent_output()` 不认识 `baseline`，返回的结构里不会有正确的 `artifact_type == "project_baseline"`。

- [ ] **Step 3: Write the minimal formatter implementation**

```python
def format_agent_output(data: dict[str, Any]) -> dict[str, Any]:
    """Return compact, action-oriented output for an existing runtime result."""

    if "context_pack" in data:
        return _context_pack_output(data["context_pack"])
    if "impact_analysis" in data:
        output = _impact_analysis_output(data["impact_analysis"])
        if "git_diff" in data:
            output["git_diff"] = data["git_diff"]
        return output
    if "baseline" in data:
        return _project_baseline_output(data["baseline"])
    return data


def _project_baseline_output(baseline: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_type": "project_baseline",
        "project_id": baseline.get("project_id"),
        "project_summary": baseline.get("project_summary"),
        "project_goal": baseline.get("project_goal"),
        "primary_users": baseline.get("primary_users", []),
        "core_modules": baseline.get("core_modules", []),
        "key_flows": baseline.get("key_flows", []),
        "third_party_integrations": baseline.get("third_party_integrations", []),
        "high_risk_areas": baseline.get("high_risk_areas", []),
        "constraints": baseline.get("constraints", []),
        "validation_strategy": baseline.get("validation_strategy", []),
        "priority_evidence": baseline.get("priority_evidence", []),
        "unknowns": baseline.get("unknowns", []),
        "quality_notes": baseline.get("quality_notes", []),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python3.11 -m unittest tests.test_agent_output -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_agent_output.py packages/runtime/projectbrain_runtime/agent_output.py
git commit -m "feat(agent): add baseline agent output formatter"
```

---

### Task 2: `feat/v1-32-baseline-agent-cli`

**Files:**
- Modify: `packages/runtime/projectbrain_cli/main.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing CLI test for `baseline show --format agent`**

Add to `tests/test_cli.py`:

```python
    def test_baseline_show_agent_format_returns_project_baseline_view(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            store_root = str((Path(tmp) / "store").resolve())

            _run_cli(
                [
                    "--store-root",
                    store_root,
                    "import",
                    str(fixture["project_path"]),
                    "--id",
                    "payment_baseline_show_agent_cli",
                    "--experience-seed",
                    str(fixture["experience_seed"]),
                ]
            )

            started = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "intake",
                    "project",
                    "payment_baseline_show_agent_cli",
                ]
            )

            _run_cli(
                [
                    "--store-root",
                    store_root,
                    "intake",
                    "answer",
                    "payment_baseline_show_agent_cli",
                    started["intake"]["session_id"],
                    "--answer",
                    "这个项目主要负责支付回调和结算处理。",
                ]
            )

            output = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "baseline",
                    "show",
                    "payment_baseline_show_agent_cli",
                    "--format",
                    "agent",
                ]
            )

            self.assertEqual(output["agent_output"]["artifact_type"], "project_baseline")
            self.assertEqual(output["agent_output"]["project_id"], "payment_baseline_show_agent_cli")
            self.assertEqual(output["agent_output"]["project_goal"], "这个项目主要负责支付回调和结算处理。")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3.11 -m unittest tests.test_cli.ProjectBrainCliTest.test_baseline_show_agent_format_returns_project_baseline_view -v
```

Expected: FAIL，`argparse` 报 `unrecognized arguments: --format agent`。

- [ ] **Step 3: Write the failing CLI test for `baseline build --format agent`**

Add to `tests/test_cli.py`:

```python
    def test_baseline_build_agent_format_returns_project_baseline_view(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = create_payment_mini_codegraph_project(Path(tmp))
            store_root = str((Path(tmp) / "store").resolve())

            _run_cli(
                [
                    "--store-root",
                    store_root,
                    "import",
                    str(fixture["project_path"]),
                    "--id",
                    "payment_baseline_build_agent_cli",
                    "--experience-seed",
                    str(fixture["experience_seed"]),
                ]
            )

            started = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "intake",
                    "project",
                    "payment_baseline_build_agent_cli",
                ]
            )

            answered = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "intake",
                    "answer",
                    "payment_baseline_build_agent_cli",
                    started["intake"]["session_id"],
                    "--answer",
                    "这个项目主要负责支付回调和结算处理。",
                ]
            )
            Path(answered["baseline_artifact_path"]).unlink()

            output = _run_cli(
                [
                    "--store-root",
                    store_root,
                    "baseline",
                    "build",
                    "payment_baseline_build_agent_cli",
                    "--format",
                    "agent",
                ]
            )

            self.assertEqual(output["agent_output"]["artifact_type"], "project_baseline")
            self.assertEqual(output["agent_output"]["project_id"], "payment_baseline_build_agent_cli")
            self.assertEqual(output["agent_output"]["project_goal"], "这个项目主要负责支付回调和结算处理。")
```

- [ ] **Step 4: Run test to verify it fails**

Run:

```bash
python3.11 -m unittest tests.test_cli.ProjectBrainCliTest.test_baseline_build_agent_format_returns_project_baseline_view -v
```

Expected: FAIL，`argparse` 报 `unrecognized arguments: --format agent`。

- [ ] **Step 5: Write the minimal CLI implementation**

Update parser registration:

```python
    baseline_build = baseline_subcommands.add_parser("build", help="Build the latest project baseline artifact")
    baseline_build.add_argument("project_id")
    baseline_build.add_argument("--format", choices=OUTPUT_FORMATS, default="json", help="Output format")
    baseline_show = baseline_subcommands.add_parser("show", help="Show the latest project baseline artifact")
    baseline_show.add_argument("project_id")
    baseline_show.add_argument("--format", choices=OUTPUT_FORMATS, default="json", help="Output format")
```

Update dispatch:

```python
    if args.command == "baseline":
        if args.baseline_command == "build":
            data = runtime.build_project_baseline(project_id=args.project_id)
            print_json(format_output(data, args.format))
            return 0
        if args.baseline_command == "show":
            data = {
                "artifact_path": str(
                    Path(args.store_root)
                    / "projects"
                    / args.project_id
                    / "runs"
                    / "project-baseline-latest.json"
                ),
                "baseline": repository.get_run_artifact(args.project_id, "project-baseline-latest.json"),
            }
            print_json(format_output(data, args.format))
            return 0
        raise ValueError(f"Unsupported baseline command: {args.baseline_command}")
```

- [ ] **Step 6: Run tests to verify they pass**

Run:

```bash
python3.11 -m unittest \
  tests.test_cli.ProjectBrainCliTest.test_baseline_show_agent_format_returns_project_baseline_view \
  tests.test_cli.ProjectBrainCliTest.test_baseline_build_agent_format_returns_project_baseline_view -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add packages/runtime/projectbrain_cli/main.py tests/test_cli.py
git commit -m "feat(cli): add baseline agent output format"
```

---

### Task 3: `feat/v1-32-baseline-agent-docs-and-verify`

**Files:**
- Modify: `README.md`
- Modify: `docs/projectbrain/local-runtime.md`
- Verify: `packages/runtime/projectbrain_runtime/agent_output.py`
- Verify: `packages/runtime/projectbrain_cli/main.py`
- Verify: `tests/test_agent_output.py`
- Verify: `tests/test_cli.py`

- [ ] **Step 1: Update README examples**

Add the new commands near the existing Baseline examples:

```md
projectbrain baseline build my_project
projectbrain baseline build my_project --format agent
projectbrain baseline show my_project
projectbrain baseline show my_project --format agent
```

Add one explanatory sentence:

```md
`baseline build` 和 `baseline show` 现在也支持 `--format agent`，可直接返回面向 AI 编程智能体的紧凑项目基线结构。
```

- [ ] **Step 2: Update local runtime docs**

Update `docs/projectbrain/local-runtime.md` command description:

```md
`intake project` currently starts a minimal eight-step onboarding flow: capture the project goal, primary users, core modules, key flows, third-party integrations, high-risk areas, constraints, and validation strategy, while keeping `project-intake-session-latest.json` plus a lightweight `baseline_draft` in sync. Each `intake answer` also refreshes `runs/project-baseline-latest.json` for downstream consumption, `baseline build <project_id>` rebuilds that artifact from the latest intake session, and both `baseline build <project_id> --format agent` plus `baseline show <project_id> --format agent` return a compact baseline view for AI coding agents.
```

- [ ] **Step 3: Run focused regression**

Run:

```bash
python3.11 -m unittest tests.test_agent_output tests.test_cli -v
```

Expected: PASS.

- [ ] **Step 4: Run broader regression**

Run:

```bash
python3.11 -m unittest tests.test_bundle tests.test_cli tests.test_repository tests.test_agent_output -v
```

Expected: PASS.

- [ ] **Step 5: Check diagnostics**

Use diagnostics for:

```text
packages/runtime/projectbrain_runtime/agent_output.py
packages/runtime/projectbrain_cli/main.py
tests/test_agent_output.py
tests/test_cli.py
```

Expected: no new diagnostics.

- [ ] **Step 6: Commit**

```bash
git add README.md docs/projectbrain/local-runtime.md
git commit -m "docs: document baseline agent output"
```

- [ ] **Step 7: Push and merge back to product branch**

Run:

```bash
git push -u origin feat/v1-32-baseline-agent-output
git checkout feat/v1-product
git merge --ff-only feat/v1-32-baseline-agent-output
```

Expected: push succeeds and `feat/v1-product` fast-forwards cleanly.

---

## Validation Matrix

**Formatter**
- `python3.11 -m unittest tests.test_agent_output -v`

**CLI**
- `python3.11 -m unittest tests.test_cli.ProjectBrainCliTest.test_baseline_show_agent_format_returns_project_baseline_view -v`
- `python3.11 -m unittest tests.test_cli.ProjectBrainCliTest.test_baseline_build_agent_format_returns_project_baseline_view -v`

**Branch regression**
- `python3.11 -m unittest tests.test_agent_output tests.test_cli -v`
- `python3.11 -m unittest tests.test_bundle tests.test_cli tests.test_repository tests.test_agent_output -v`

---

## Spec Coverage Check

- `baseline show --format agent`：由 Task 2 覆盖。
- `baseline build --format agent`：由 Task 2 覆盖。
- 统一 formatter 投影：由 Task 1 覆盖。
- 文档收口：由 Task 3 覆盖。
- 默认 JSON 行为不变：由 Task 2 的最小分发改动和原有 JSON 测试共同保障。

## Placeholder Scan

- 无 `TODO`、`TBD`、`similar to` 之类占位语。
- 所有测试步骤都包含实际命令与预期失败/成功信号。
- 所有代码改动步骤都给出最小实现片段。

## Type Consistency Check

- Agent 输出统一使用 `artifact_type == "project_baseline"`。
- CLI 参数统一使用 `--format` 和 `OUTPUT_FORMATS`。
- Baseline 投影字段与 spec 中约定的 `project_goal`、`primary_users`、`quality_notes` 保持一致。
