"""
============================================================
企业级智能搜索代理系统 (Agentic Search System)
============================================================

基于 Doubao（豆包）大模型的企业级多源智能搜索代理。

通过 ReAct（Reasoning + Acting）模式，让 Doubao 模型自主决策：
1. 应该搜索哪个数据源
2. 如何构造搜索查询
3. 搜索结果是否足够
4. 下一步该搜什么
5. 何时停止搜索并给出答案

可搜索的数据源：
- 本地 SQLite 数据库（结构化数据）
- 本地 ChromaDB 向量数据库（语义搜索）
- 本地 Whoosh 关键词索引（全文检索）
- 本地代码仓库（grep/文件搜索）
- 模拟企业系统 SDK（HR/CRM/ERP/知识库）

Usage:
    from agentic_search import SearchAgent

    agent = SearchAgent()
    answer = agent.run("技术部有哪些进行中的项目？")
    print(answer)
"""

__version__ = "1.0.0"
__author__ = "Enterprise Search Team"

from .agent.core import SearchAgent
from .agent.llm import DoubaoLLM
from .agent.tools import ToolRegistry
