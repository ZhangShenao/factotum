"""实验 00：DeepSeek Agent 快速入门。
    - 无任何 middleware 时 agent 的原始行为（工具调用循环、消息流）
    - state 结构里有什么、没有什么（为后续逐层 diff 建立基线）
"""

from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent
from search_tool import internet_search
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 创建 LLM 模型
model = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL"),  # 可用 MODEL_NAME 覆盖
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)

# 定义System Prompt
research_instructions = """你是一位专业的研究员。
你的工作是进行深入研究，然后撰写一份完整的研究报告。
"""

# 创建 DeepAgent
agent = create_deep_agent(
    model=model,    # 指定 LLM 模型
    tools=[internet_search],  # 设置工具列表
    system_prompt=research_instructions,  # 指定 System Prompt
)

# 运行 Agent
result = agent.invoke(
    {"messages": [{"role": "user", "content": "DeepAgents是什么？"}]}
)

print(result["messages"][-1].content)
