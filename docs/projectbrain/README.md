# ProjectBrain Documentation

本目录是 ProjectBrain 的设计文档集。ProjectBrain 的目标是为 AI Software Engineer 提供长期项目认知与记忆层，而不是再做一个代码搜索或一次性文档生成工具。

## 阅读顺序

建议按以下顺序阅读和实现：

1. [Design Document](design-document.md)
2. [Domain Model](domain-model.md)
3. [Knowledge Schema](knowledge-schema.md)
4. [MVP Architecture](mvp-architecture.md)
5. [Implementation Plan](implementation-plan.md)
6. [Delivery Gap Analysis](delivery-gap-analysis.md)
7. [CodeGraph Integration](codegraph-integration.md)
8. [Local Runtime](local-runtime.md)
9. [v0.2 Release Readiness](../release-readiness.md)
10. [中文快速上手](../zh/quickstart.md)
11. [Refund Handling Fee Walkthrough](refund-handling-fee-walkthrough.md)
12. [Evaluation Plan](evaluation-plan.md)

## 文档职责

| Document | Responsibility |
| --- | --- |
| [Design Document](design-document.md) | Product positioning, architecture, Agent design, lifecycle, API, technology choices, roadmap, and open-source planning. |
| [Domain Model](domain-model.md) | Bounded contexts, core domain objects, enterprise Java microservice modeling, and ubiquitous language. |
| [Knowledge Schema](knowledge-schema.md) | PostgreSQL schema, graph schema, confidence model, source traceability, lifecycle, and knowledge pollution controls. |
| [MVP Architecture](mvp-architecture.md) | Deployable MVP service boundaries, Docker Compose architecture, V0.1-V1.0 capabilities, API surface, and acceptance criteria. |
| [Implementation Plan](implementation-plan.md) | Engineering phases, work breakdown, testing strategy, observability, security, open-source setup, and definition of done. |
| [Agent Skills](agent-skills.md) | Agent Skill contracts, inputs, outputs, execution policies, and failure handling. |
| [API Contract](api-contract.md) | REST API and MCP tool contract draft for implementation. |
| [Delivery Gap Analysis](delivery-gap-analysis.md) | 当前文档与实现之间还缺什么，以及下一步优先级。 |
| [CodeGraph Integration](codegraph-integration.md) | 将 CodeGraph 作为 V0.1 代码事实层，ProjectBrain 专注长期记忆、业务理解、知识治理和 Context Pack。 |
| [Local Runtime](local-runtime.md) | 当前本地 CLI、JSON runtime、FastAPI skeleton 和 synthetic demo 的使用方式。 |
| [v0.2 Release Readiness](../release-readiness.md) | v0.2 发布前的测试、CLI/MCP smoke、policy 和隐私边界检查清单。 |
| [中文快速上手](../zh/quickstart.md) | 面向中文读者的安装、demo、自有项目、MCP、claims 和隐私策略说明。 |
| [Refund Handling Fee Walkthrough](refund-handling-fee-walkthrough.md) | 用“增加退款手续费”贯穿 Brain Update、Knowledge Graph、stale claim 和 Impact Analysis。 |
| [Evaluation Plan](evaluation-plan.md) | 评估 ProjectBrain 知识质量、Context Pack、Impact Analysis、Brain Update 和 Agent 任务效果。 |

## 核心设计承诺

- ProjectBrain 是 memory layer，不是 search product。
- ProjectBrain 不重复造 CodeGraph，V0.1 优先把 CodeGraph 纳入 Fact Layer。
- 每条长期知识都必须可追溯来源。
- LLM 推理必须带 confidence 和 review state。
- 人工确认经验是一等知识类型。
- 代码变化会触发 Brain 更新和 stale knowledge 检测。
- Coding Agent 消费 scoped context pack，而不是全量 repository dump。
