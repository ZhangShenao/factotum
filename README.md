# factotum

> Personal all-round assistant agent built on [DeepAgents](https://github.com/langchain-ai/deepagents) (LangChain) — benchmarking [OpenClaw](https://github.com/openclaw/openclaw).

基于 DeepAgents 的**个人全能助理 Agent**。定位：业界顶尖的个人助理 Agent 实践；日常接入飞书等 IM，完成真实任务，解放生产力。

## 为什么做这个项目

1. **学习 DeepAgents 框架及底层原理** — 它代表了当前 harness engineering 的最新实践（middleware 组装范式、planning / subagent / 虚拟文件系统 / backfill）
2. **跟进 Agent 领域新进展** — 以此项目为锚点持续跟踪 LangChain 生态演化
3. **真实任务落地** — 接入飞书等 IM，在日常生活中真实使用（真实用户、真实场景、真实数据）

核心原则：**学习优先**。DeepAgents 层为主、LangGraph 按需深入。

## 架构：组装者路径

不用 `create_deep_agent()` 黑盒全家桶，也不用从零造轮子——从 LangChain 的
`create_agent()` 空核出发，**逐层引入 DeepAgents 的 middleware**，每层做对照实验，
最后与官方全家桶对拍：

```
filesystem → planning → summarization → subagents → HITL → backfill
```

一条产品主线 + 一条学习主线，共享同一代码库：

```
factotum/
├── assistant/              # 产品主线：CLI 助理
│   ├── agent.py            #   middleware 栈组装入口（产品的"心脏"）
│   ├── middleware/         #   自研 middleware（LTM 注入/提取、审计日志）
│   ├── tools/              #   web_search / web_fetch / shell / scheduler
│   ├── backends.py         #   CompositeBackend 路由（工作区 vs 记忆分区）
│   ├── scheduler.py        #   定时任务（APScheduler）
│   ├── cli.py              #   REPL（rich 渲染流式输出）
│   └── config.py           #   配置（.env，系统变量优先）
├── experiments/            # 学习主线：每层 middleware 一组对照实验
│   └── 00_baseline/ ... 06_backfill/
├── notes/                  # 实验结论 → 学习笔记沉淀
└── tests/
```

关键决策：

| 决策 | 选择 |
|------|------|
| 模型接入 | OpenAI 兼容 API（`OPENAI_BASE_URL` + key，任意厂商可切） |
| 持久化 | SqliteSaver（checkpointer）+ CompositeBackend（`/memories/` 独立分区） |
| LTM | v1 官方文件式（`memory` + StoreBackend），v2 实验 Store 向量检索 |
| 工具域（v1） | 联网检索 / 本地文件+shell / 待办+定时 / 长期记忆 |

## 快速开始

```bash
# 依赖管理：uv
uv sync

# 配置
cp .env.example .env  # 填入 OPENAI_API_KEY 等

# 运行（骨架阶段仅打印横幅）
uv run factotum

# 开发
uv run ruff check .
uv run ruff format .
uv run pytest
```

## 路线图

- **v1 本地 CLI**：四大工具域跑通，middleware 栈逐层组装 + 对照实验
- **v2 飞书接入**：IM 网关（消息收发 / 会话映射 thread_id / 卡片审批），CLI 与飞书双适配层
- **v3 常驻服务**：24/7 进程 + 定时唤醒 + 多会话并发

## 参考

- [DeepAgents](https://github.com/langchain-ai/deepagents) — LangChain 官方 deep agent 框架
- [OpenClaw](https://github.com/openclaw/openclaw) — 对标的个人助理 Agent 实践
- [harness9](https://github.com/harness9/harness9) — 作者用 Go 实现的 Agent Harness 框架（本项目的对照系）

## License

MIT
