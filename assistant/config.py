"""配置加载 — .env 文件 + 系统环境变量（系统变量优先）。

变量约定：
    OPENAI_BASE_URL / OPENAI_API_KEY   OpenAI 兼容 API
    FACTOTUM_MODEL                     默认模型（LangChain init_chat_model 格式）
"""

import os

from dotenv import load_dotenv

load_dotenv()


def get_config() -> dict[str, str]:
    """返回运行配置。系统环境变量优先于 .env 文件。"""
    return {
        "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "model": os.getenv("FACTOTUM_MODEL", "openai:gpt-4o"),
    }
