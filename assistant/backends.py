"""CompositeBackend 路由 — 工作区 vs 记忆分区。

设计：
    - 工作区文件路由到本地目录（FilesystemBackend）
    - /memories/ 前缀路由到独立持久存储（StoreBackend），跨会话长期记忆

骨架阶段：仅保留结构占位。
"""
