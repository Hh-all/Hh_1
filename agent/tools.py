"""
============================================================
工具注册表 - 定义所有可用的搜索工具
Tool Registry with OpenAI Function Calling Format
============================================================

这里定义了搜索代理可以使用的所有"工具"（搜索后端），
每个工具都有清晰的描述、参数定义和使用说明，
供 Doubao 模型在推理时选择调用。

工具设计原则：
1. 每个工具的 description 要清晰说明何时应该使用它
2. parameters 要有良好的 JSON Schema 定义
3. 描述中要包含使用场景的提示，帮助 LLM 做决策
"""
import json
import time
from typing import Any, Dict, Optional

from logger_setup import log


class ToolRegistry:
    """
    工具注册表 - 管理所有搜索工具。

    负责：
    1. 维护工具定义（OpenAI function calling 格式）
    2. 执行工具调用并返回结果
    3. 记录每个工具的调用历史
    """

    def __init__(self):
        self._tools: Dict[str, dict] = {}       # name → tool_definition
        self._handlers: Dict[str, callable] = {} # name → handler function
        self.call_history: list = []             # 工具调用历史
        self._register_all_tools()

    def get_definitions(self) -> list:
        """获取所有工具的 OpenAI function calling 格式定义"""
        return list(self._tools.values())

    def execute(self, tool_name: str, arguments: dict) -> str:
        """
        执行指定的工具。

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果字符串
        """
        if tool_name not in self._handlers:
            return f"错误: 未知工具 '{tool_name}'。可用工具: {list(self._handlers.keys())}"

        handler = self._handlers[tool_name]
        query = arguments.get("query", "")

        log.info(f"[工具执行] ▶ {tool_name} | query='{query[:80]}...'")

        start_time = time.time()
        try:
            result = handler(**arguments)
            elapsed = time.time() - start_time

            # 记录调用历史
            record = {
                "tool": tool_name,
                "query": query,
                "result_length": len(result),
                "elapsed": f"{elapsed:.2f}s",
                "timestamp": time.time(),
            }
            self.call_history.append(record)

            log.info(f"[工具执行] ✅ {tool_name} | 结果长度={len(result)} | 耗时={elapsed:.2f}s")
            return result

        except Exception as e:
            log.error(f"[工具执行] ❌ {tool_name} 执行失败: {e}")
            return f"工具执行错误: {e}"

    def get_call_summary(self) -> str:
        """获取工具调用摘要"""
        if not self.call_history:
            return "尚未调用任何工具。"

        lines = [f"工具调用历史（共 {len(self.call_history)} 次）:"]
        for i, record in enumerate(self.call_history, 1):
            lines.append(
                f"  {i}. {record['tool']} | "
                f"query='{record['query'][:50]}...' | "
                f"结果={record['result_length']}字符 | "
                f"耗时={record['elapsed']}"
            )
        return "\n".join(lines)

    # ================================================================
    # 私有方法: 注册所有工具
    # ================================================================

    def _register_all_tools(self):
        """注册所有可用的搜索工具"""
        self._register_tool(
            name="search_local_database",
            description=(
                "【本地关系数据库搜索】适合查询结构化数据，如：员工信息、部门数据、"
                "项目记录、销售报表、财务数据等表格化信息。\n"
                "使用场景：当用户询问具体的数据记录、统计数字、人员名单时优先使用。\n"
                "可以输入SQL语句（如 SELECT * FROM employees WHERE department='技术部'）"
                "或自然语言描述（如 '技术部所有员工'）。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "SQL查询语句或自然语言数据查询描述。\n"
                            "SQL示例: SELECT * FROM employees WHERE department='技术部'\n"
                            "自然语言示例: '查询技术部的所有员工信息' 或 '项目进度统计'"
                        ),
                    }
                },
                "required": ["query"],
            },
            handler=self._search_db,
        )

        self._register_tool(
            name="search_vector_database",
            description=(
                "【向量语义搜索】基于语义相似度进行搜索，适合查找概念相关的内容。\n"
                "使用场景：当用户的问题比较抽象、概念化，或需要理解语义而非精确匹配时使用。\n"
                "例如：查找'如何提升系统性能'相关的所有文档，或'数据安全的最佳实践'。\n"
                "适用于查找：技术文档、产品说明、会议纪要、知识库文章等非结构化文本。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "用自然语言描述的搜索意图，越具体越好",
                    }
                },
                "required": ["query"],
            },
            handler=self._search_vector,
        )

        self._register_tool(
            name="search_keywords",
            description=(
                "【关键词全文检索】基于精确关键词匹配的全文搜索，适合查找包含特定术语的文档。\n"
                "使用场景：当搜索特定术语、产品名称、人名、编号等精确关键词时使用。\n"
                "例如：搜索所有包含 '等保2.0' 或 'Kubernetes' 的文档。\n"
                "相比向量搜索，关键词搜索更精确但不会做语义扩展。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词或短语，空格分隔多个关键词",
                    }
                },
                "required": ["query"],
            },
            handler=self._search_keywords,
        )

        self._register_tool(
            name="search_code_repository",
            description=(
                "【代码仓库搜索】搜索本地代码文件，支持按文件名、代码内容、函数/类定义搜索。\n"
                "使用场景：当用户询问与技术实现、代码逻辑、函数定义相关的问题时使用。\n"
                "查询格式：\n"
                "- 'file:xxx' 按文件名搜索\n"
                "- 'def xxx' 或 'func:xxx' 搜索函数定义\n"
                "- 'class xxx' 搜索类定义\n"
                "- 直接输入关键词则搜索代码内容\n"
                "- 'list' 列出所有文件"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "代码搜索查询。支持格式: file:文件名 / def 函数名 / "
                            "class 类名 / 关键词grep搜索 / list列出文件"
                        ),
                    }
                },
                "required": ["query"],
            },
            handler=self._search_code,
        )

        self._register_tool(
            name="query_enterprise_system",
            description=(
                "【企业内部系统查询】模拟的企业内部信息化系统，包含：\n"
                "- HR系统: 员工信息、部门组织架构、联系方式\n"
                "- CRM系统: 客户信息、客户等级、销售管道\n"
                "- ERP系统: 库存物料、仓库信息、资产总览\n"
                "- 知识库: 公司制度、流程规范、技术标准\n"
                "- 项目管理系统: 项目进度、预算、负责人\n\n"
                "使用场景：当用户询问公司内部信息（如员工、客户、库存、制度流程、项目进度）时使用。\n"
                "系统会自动识别查询类型并路由到正确的子系统。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "对企业内部系统的查询，可以是员工名、部门名、客户名、物料名、制度类型等",
                    }
                },
                "required": ["query"],
            },
            handler=self._search_enterprise,
        )

    def _register_tool(self, name: str, description: str, parameters: dict, handler: callable):
        """注册单个工具"""
        tool_def = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            }
        }
        self._tools[name] = tool_def
        self._handlers[name] = handler

    # ================================================================
    # 工具处理函数（延迟初始化后端实例）
    # ================================================================

    @property
    def _db(self):
        if not hasattr(self, '_db_instance'):
            from backends.database import LocalDatabase
            self._db_instance = LocalDatabase()
        return self._db_instance

    @property
    def _vector(self):
        if not hasattr(self, '_vector_instance'):
            from backends.vector_db import VectorDatabase
            self._vector_instance = VectorDatabase()
        return self._vector_instance

    @property
    def _keyword(self):
        if not hasattr(self, '_keyword_instance'):
            from backends.keyword_search import KeywordSearchEngine
            self._keyword_instance = KeywordSearchEngine()
        return self._keyword_instance

    @property
    def _code(self):
        if not hasattr(self, '_code_instance'):
            from backends.code_repo import CodeRepository
            self._code_instance = CodeRepository()
        return self._code_instance

    @property
    def _enterprise(self):
        if not hasattr(self, '_enterprise_instance'):
            from backends.enterprise_sdk import EnterpriseSDK
            self._enterprise_instance = EnterpriseSDK()
        return self._enterprise_instance

    def _search_db(self, query: str) -> str:
        return self._db.search(query)

    def _search_vector(self, query: str) -> str:
        return self._vector.search(query)

    def _search_keywords(self, query: str) -> str:
        return self._keyword.search(query)

    def _search_code(self, query: str) -> str:
        return self._code.search(query)

    def _search_enterprise(self, query: str) -> str:
        return self._enterprise.query(query)
