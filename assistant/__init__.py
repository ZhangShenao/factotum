"""Factotum — 基于 DeepAgents (LangChain) 的个人全能助理。

包结构：
    agent.py        middleware 栈组装入口（产品的"心脏"）
    middleware/     自研 middleware（LTM 注入/提取、审批日志等）
    tools/          工具集（web_search / web_fetch / shell / scheduler）
    backends.py     CompositeBackend 路由（工作区 vs 记忆分区）
    scheduler.py    定时任务调度（APScheduler）
    cli.py          REPL 入口（rich 渲染流式输出）
    config.py       配置加载（.env，系统环境变量优先）
"""

__version__ = "0.1.0"
