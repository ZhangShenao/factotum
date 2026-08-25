"""Agent 组装入口 — factotum 的"心脏"。

组装路径（学习主线即构建顺序）：从 LangChain 的 create_agent() 空核出发，
逐层引入 DeepAgents 的 middleware：

    filesystem → planning → summarization → subagents → HITL → backfill

每层做三件事：① 读官方实现 → ② 对照实验（有/无该层的行为 diff + state dump）
→ ③ 笔记沉淀（notes/）。全部挂完后与 create_deep_agent() 全家桶对拍，验证
行为等价。

关键决策：
    - checkpointer: SqliteSaver（会话恢复，为飞书阶段常驻服务打底）
    - backend: CompositeBackend（/memories/ 路由到独立存储，工作区路由本地目录）
    - LTM: v1 用官方文件式（memory + StoreBackend 分区），v2 实验 Store 向量检索

骨架阶段：仅保留结构占位，不含实现。
"""


def build_agent():  # noqa: ANN201 - 骨架阶段暂不约束返回类型
    """组装 middleware 栈，返回可 invoke 的 agent。"""
    raise NotImplementedError("骨架阶段：按 docstring 中的组装路径逐层实现")
