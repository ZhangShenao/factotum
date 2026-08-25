"""定时任务调度 — APScheduler。

设计：定时唤醒 = 以新 thread_id invoke agent（复用 checkpointer 状态），
而非进程内常驻循环。飞书阶段接入常驻服务时启用。

骨架阶段：仅保留结构占位。
"""
