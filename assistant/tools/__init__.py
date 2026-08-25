"""工具集 — v1 四大工具域。

    - 联网信息检索：web_search / web_fetch（参考 harness9 的 SSRF 防护设计）
    - 本地文件/shell：DeepAgents 内置 filesystem 工具 + shell 执行
    - 待办/定时任务：todo 工具 + scheduler 唤醒
    - 长期记忆：memory 工具（读写 /memories/ 分区）

骨架阶段：仅保留结构占位。
"""
