"""自研 middleware — LTM 注入/提取、审批日志等。

规划中的 middleware（均为 AgentMiddleware 子类或 wrap_model_call/wrap_tool_call
函数式拦截器）：
    - MemoryInjectionMiddleware   每轮注入长期记忆精华（MEMORY.md 物化视图）
    - MemoryExtractMiddleware     会话结束/压缩前提取事实写入 LTM
    - AuditLogMiddleware          工具调用审计日志

骨架阶段：仅保留结构占位。
"""
