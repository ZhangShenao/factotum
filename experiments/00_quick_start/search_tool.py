"""
网络搜索工具

Tool三要素:
Docstring：告诉 Agent 这个工具的用途,它决定了 Tool 的调用时机
参数类型标注：告诉 Agent 每个参数该传什么类型，它决定了 Tool 的 Schema
默认值：标记哪些参数是可选的，它减少了必填项，降低了 LLM 的出错概率

"""

import os
from typing import Literal
from tavily import TavilyClient
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 初始化 Tavily 客户端
tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

# 构造网络搜索工具
# 在LangChain的新版本中，普通的Python函数可以作为工具直接使用，而无需再使用 @tool 装饰器

def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search for the given query.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return.
        topic: The topic category for the search.
        include_raw_content: Whether to include raw page content.
    """
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )