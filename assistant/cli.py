"""REPL 入口 — rich 渲染流式输出。

骨架阶段：仅打印横幅。实现时接入 build_agent() 的流式输出与
LiteLLM/langchain 流式事件（token / tool call / thinking）。
"""

import rich

from assistant import __version__


def main() -> None:
    """CLI 入口（pyproject [project.scripts] factotum = "assistant.cli:main"）。"""
    rich.print(f"[bold]factotum[/bold] v{__version__} — 骨架阶段，CLI 尚未实现")


if __name__ == "__main__":
    main()
