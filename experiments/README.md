# 实验方法论

每层 middleware 的学习遵循**对照实验三步法**：

1. **读官方实现** — 定位 DeepAgents 源码中该 middleware 的实现，理解其 state 注入 / model-call 包装 / tool-call 拦截方式
2. **对照实验** — 有/无该层的 A/B 运行，观察行为 diff + LangGraph state dump + trace
3. **笔记沉淀** — 结论写入 `notes/<NN>-<topic>.md`

## 实验目录

| 目录 | 主题 | 核心验证点 |
|------|------|-----------|
| `00_baseline/` | 裸 create_agent() 空核 | 无 middleware 时的原始 agent 行为基线 |
| `01_filesystem/` | FilesystemMiddleware | StateBackend vs FilesystemBackend vs CompositeBackend；files state 与磁盘同步时机 |
| `02_planning/` | PlanningMiddleware | todos 状态注入方式；plan-then-execute 行为是否涌现 |
| `03_summarization/` | SummarizationMiddleware | 压缩触发点（阈值/条数）；摘要质量与信息保留对照 |
| `04_subagents/` | SubAgentMiddleware | task 工具委派行为；子代理上下文隔离验证 |
| `05_hitl/` | HumanInTheLoop | interrupt_on + checkpointer 协作；中断恢复语义 |
| `06_backfill/` | 后台任务回填 | 后台任务与结果回填线程模型 |

## 约定

- 每个实验独立可运行：`uv run python -m experiments.<NN>_topic>.exp`
- 实验脚本只依赖 `assistant/` 公开接口与 DeepAgents 官方 API，不复制框架内部代码
- 每组实验必须留下 state dump 证据（打印或保存到 `notes/evidence/`）
