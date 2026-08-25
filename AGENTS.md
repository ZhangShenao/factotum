# AGENTS.md — factotum 项目开发指南

## 1. 项目概述

factotum（拉丁语"做一切事的人"）是一款基于 **DeepAgents (LangChain)** 的**个人全能助理 Agent**，对标 OpenClaw。最终形态：接入飞书等 IM 的常驻个人助理，在日常生活中完成真实任务。

### 三大动机与优先级

| 动机 | 优先级 |
|------|--------|
| 学习 DeepAgents 框架及底层原理（harness engineering 最新实践） | **第一** |
| 跟进 Agent 领域新进展 | 第二 |
| 真实任务落地（飞书接入，解放生产力） | 第三 |

**冲突裁决原则：学习优先。** 为了学透机制，可以接受功能后置；但产品主线（`assistant/`）始终同步演进，学习实验（`experiments/`）的结论必须反哺产品侧。

### 构建策略：组装者路径（方案 B）

DeepAgents 不是独立框架，而是 LangChain agent middleware 体系上的一层组装。本项目：

- **不用** `create_deep_agent()` 黑盒全家桶直接拼装（学不到东西）
- **不从零** 复刻一个 mini-DeepAgents（边际学习价值低，harness9 已造过轮子）
- **从 `create_agent()` 空核出发，逐层引入官方 middleware**，每层做对照实验，最后与全家桶对拍

组装顺序（依赖关系决定，不可乱序）：

```
filesystem → planning → summarization → subagents → HITL → backfill
```

顺序理由：filesystem 是 state 扩展的最小案例；planning/summarization 是纯 model-call 包装；subagents 引入嵌套 agent（复杂度跳档）；HITL 依赖 checkpointer（必须后置）；backfill 是最上层的糖。

### 核心架构决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 模型接入 | OpenAI 兼容 API | 一个 base_url + key 任意厂商可切 |
| checkpointer | SqliteSaver | 会话恢复；为飞书阶段常驻服务打底 |
| backend | CompositeBackend | `/memories/` 路由独立存储，工作区路由本地目录 |
| LTM | v1 文件式（`memory` + StoreBackend）；v2 Store 向量检索 | 文件式即官方最佳实践，v2 本身是一组学习实验 |
| 定时任务 | APScheduler，唤醒 = 新 thread invoke | 不做进程内常驻循环，复用 checkpointer 状态 |
| CLI 渲染 | rich | 流式输出（token / tool call / thinking） |

### 对照系

- **harness9**（作者前作，Go）：planning / 压缩 / 子代理 / LTM 均有独立实现，每层实验必须做两侧设计对照
- **OpenClaw**：IM 接入 / 常驻服务 / 权限审批层的形态对标

---

## 2. 技术栈

| 依赖 | 用途 |
|------|------|
| Python ≥ 3.12 | 运行时（本地开发用 3.13） |
| [uv](https://docs.astral.sh/uv/) | 依赖与虚拟环境管理（锁定 `uv.lock`） |
| `deepagents` | middleware 栈（Filesystem/Planning/Summarization/SubAgent/HITL/backfill） |
| `langchain` / `langgraph` | `create_agent()` 空核 / checkpointer / state |
| `python-dotenv` | 配置加载（系统变量优先） |
| `rich` | CLI 流式渲染 |
| `apscheduler` | 定时任务（飞书阶段启用） |
| `pytest` / `ruff` | 测试 / Lint+Format（dev group） |

---

## 3. 项目结构

```
factotum/
├── assistant/                  # 产品主线
│   ├── agent.py                #   middleware 栈组装入口
│   ├── middleware/             #   自研 middleware（LTM 注入/提取、审计日志）
│   ├── tools/                  #   工具集（web/shell/todo/memory）
│   ├── backends.py             #   CompositeBackend 路由
│   ├── scheduler.py            #   APScheduler 定时唤醒
│   ├── cli.py                  #   REPL 入口（uv run factotum）
│   └── config.py               #   配置加载
├── experiments/                # 学习主线：00_baseline ... 06_backfill
│   └── README.md               #   对照实验三步法与约定
├── notes/                      # 实验结论沉淀（每组实验一份笔记）
├── tests/                      # pytest
├── .github/workflows/ci.yml    # CI：uv sync --frozen + ruff + pytest
├── .opencode/                  # OpenCode 配置（commands，见 §7）
├── .claude/                    # Claude Code 兼容配置（CLAUDE.md → AGENTS.md）
├── opencode.json               # OpenCode root 配置（superpowers 插件 + context7 MCP）
├── .mcp.json                   # MCP 服务器（context7）
└── AGENTS.md                   # 本文件
```

---

## 4. 实验方法论（学习主线的 Definition of Done）

每层 middleware 按**对照实验三步法**推进：

1. **读官方实现** — 定位 DeepAgents 源码，理解 state 注入 / model-call 包装 / tool-call 拦截方式
2. **对照实验** — 有/无该层 A/B 运行，观察行为 diff + state dump + trace
3. **笔记沉淀** — 结论写入 `notes/<NN>-<topic>.md`（结论先行 → 证据 → 与 harness9 对照 → 对产品侧的影响）

强制要求：

- 实验脚本只依赖 `assistant/` 公开接口与官方 API，**不复制框架内部代码**
- 每组实验必须留下 state dump 证据
- 实验结论若影响产品侧，必须同步落地到 `assistant/` 的注释或设计文档

---

## 5. 编码规范

### 格式化与 Lint

- 所有代码必须通过 `uv run ruff check .` 和 `uv run ruff format --check .`
- 行宽 100，target py312，规则集 `E/F/W/I/UP/B`

### 命名与风格

- 模块/函数/变量：`snake_case`；类：`PascalCase`；常量：`camelCase` 或 `UPPER_SNAKE`（跟随 Python 惯例，模块级常量用 `UPPER_SNAKE`）
- docstring 与注释：中文描述设计理念（"为什么"），公开 API 签名用类型注解完整约束
- 所有公开函数必须有完整类型注解（骨架占位除外，需标注 `TODO`）

### 错误处理

- 显式处理所有异常，禁止裸 `except:`
- 错误消息不以大写字母开头、不以句号结尾（沿用 harness9 惯例，便于日志检索）
- 工具执行失败以结构化结果回传给 LLM 触发自愈，不中断循环

### 测试

- `pytest`，表驱动优先，测试文件与被测模块同构命名（`xxx.py` ↔ `test_xxx.py`）
- 运行：`uv run pytest`
- 提交前必须全绿：`uv run ruff check . && uv run ruff format --check . && uv run pytest`

### 配置加载

- `.env` 文件 + `python-dotenv`，**系统环境变量优先**
- `.env` 不入库（`.gitignore` 已排除），模板见 `.env.example`
- 新增配置项必须同步更新 `.env.example`

---

## 6. Git 工作流

- 主分支：`main`
- 功能分支命名：`feature/<描述>`、`fix/<描述>`、`chore/<描述>`、`experiment/<NN>-<topic>`
- Commit 消息：中文，聚焦"为什么"而非"做了什么"
- 提交前必须通过 CI 本地等价命令（ruff + pytest）
- 通过 PR 合并；`experiments/` 新增实验可与对应 `notes/` 笔记同 PR

---

## 7. OpenCode / Claude 配置

早期从 harness9 迁移的配置中，harness9 专用部分（知识库日报 agents、harness-researcher、test-runner、release-cli skill、sync-to-obsidian 插件与 hook）已全部移除，仅保留通用部分：

| 类别 | 位置 | 说明 |
|------|------|------|
| Commands | `.opencode/commands/`（commit / cr / pr） | 通用 Git 工作流命令 |
| MCP | `.mcp.json` + `opencode.json`（context7 + superpowers 插件） | 通用 |

> 注意：`.opencode/node_modules/` 为插件自动安装产物，不入库；opencode 首次运行会按 `opencode.json` 中的 git 引用自动重装。

---

## 8. 安全约束

- `.env` 含 API Key，**禁止提交**
- `web_fetch` / `web_search` 实现时必须带 SSRF 防护（参考 harness9 `web_safety.go` 的 9 段 IP 检查设计）
- shell / 文件工具上线前必须先实现审批层（HITL middleware + 危险模式检测）
- 飞书阶段的入站消息必须校验签名，出站操作必须过审批
