"""
============================================================
搜索代理核心 - ReAct (Reasoning + Acting) 循环
Agent Core with Iterative Reasoning Loop
============================================================

这是整个系统的核心：
1. 接收用户问题
2. Doubao 思考 → 决策 → 选择搜索工具 → 执行搜索
3. Doubao 审阅搜索结果 → 判断信息是否充足
4. 如果不充足 → 继续搜索（可能换一个工具/查询）
5. 如果充足 → 综合所有信息给出最终答案

整个过程被完整记录到日志系统中。
"""
import json
import time
from typing import Optional, Dict, Any, List

from .llm import DoubaoLLM
from .tools import ToolRegistry
from config import MAX_SEARCH_ITERATIONS
from logger_setup import log


# ================================================================
# 系统提示词 - 引导 Doubao 进行推理和决策
# ================================================================

SYSTEM_PROMPT = """# 角色定义

你是一个企业级智能搜索代理（Enterprise Search Agent）。你的任务是通过搜索多种本地数据源来回答用户的问题。

# 可用的搜索工具

你可以使用以下5种搜索工具，每种工具适用于不同的场景：

| 工具名称 | 适用场景 | 最佳使用时机 |
|---------|---------|------------|
| search_local_database | 结构化数据（员工/项目/销售） | 需要具体数字、名单、统计时 |
| search_vector_database | 语义搜索（文档/知识） | 概念性问题、需要理解上下文时 |
| search_keywords | 精确关键词匹配 | 查找特定术语、名称、编号时 |
| search_code_repository | 代码搜索 | 技术实现、函数定义、代码逻辑 |
| query_enterprise_system | 企业系统（HR/CRM/ERP/知识库） | 内部信息、制度流程、客户库存 |

# 工作流程（严格遵循）

对于用户的每个问题，你需要按照以下步骤进行：

## 第1步：分析问题
在脑海中分析用户问题的关键信息需求：
- 用户想要知道什么？
- 这个问题涉及哪些领域？（人事？技术？业务？制度？）
- 哪种数据源最可能包含相关信息？

## 第2步：制定搜索策略
确定第一步应该搜索哪个工具：
- 如果有明确的实体名称（人名、部门名、项目名）→ 优先使用企业系统查询或数据库搜索
- 如果是概念性、抽象问题 → 优先使用向量语义搜索
- 如果涉及特定术语或代码 → 使用关键词搜索或代码仓库搜索
- 永远选择最匹配的工具，而不是同时调用多个

## 第3步：执行搜索
调用选定的工具，构造一个有价值的查询：
- 查询要具体，包含关键实体名称
- 查询要简洁，不要写成完整的句子
- 如果第一次搜索不理想，换一个角度或关键词重试

## 第4步：评估结果
仔细阅读搜索结果，判断：
- ✅ 信息是否足够回答用户的问题？
- ❌ 是否缺少关键细节？
- ❌ 是否需要从另一个角度/数据源补充信息？
- ❌ 搜索结果是否完全不相关（需要换策略）？

## 第5步：决定下一步
- 如果信息充足 → 停止搜索，开始组织答案
- 如果信息不足 → 选择下一个最合适的工具，返回第3步
- 如果某个工具没搜到 → 换一个不同的搜索方式，不要重复同样的查询

## 第6步：给出最终答案
当你认为已经收集到足够的信息时，不要再调用工具，直接给出完整答案。
答案要求：
- 结构清晰，分点列出
- 引用具体的数据（数字、名称、日期）
- 注明信息来源（从哪个系统查到的）
- 如果某些信息确实找不到，诚实说明

# 重要注意事项

1. **每次只调用一个工具**：除非有明确理由需要并行搜索，否则一次只搜索一个数据源
2. **不要重复搜索**：如果某个工具已经搜过了且没有结果，尝试不同的查询或工具
3. **搜索最多3-5轮**：不要无休止地搜索，3-5轮后即使信息不完全也应该给出答案
4. **诚实透明**：告诉用户你搜了什么、找到了什么、没找到什么
5. **思考过程**：在每次调用工具前，先用文字说明你的推理过程（为什么选这个工具，期望找到什么）

# 示例对话

用户: "技术部有哪些项目在进行中？"

你的思考: 这是关于项目状态的结构化查询。技术部的项目信息最可能在本地数据库的项目表中，或者在企业系统的项目管理模块中。我先查数据库。

→ 调用 search_local_database(query="SELECT * FROM projects WHERE department='技术部' AND status='进行中'")

（获得结果后）你的评估: 数据库返回了2个项目，信息比较完整。但我还想确认一下企业系统里是否有更多细节，比如预算使用情况。

→ 调用 query_enterprise_system(query="技术部进行中的项目")

（获得结果后）你的决定: 两个数据源信息互相印证，已经足够回答用户问题了。

最终答案: （综合两个来源，列出所有进行中的项目及其详细信息）
"""


# ================================================================
# 搜索代理
# ================================================================

class SearchAgent:
    """
    智能搜索代理 - ReAct 循环核心。

    工作流程：
    1. 接收用户问题
    2. 循环：LLM推理 → 工具调用 → 结果反馈
    3. 当 LLM 认为信息充足时，生成最终答案
    """

    def __init__(self, llm: Optional[DoubaoLLM] = None, tools: Optional[ToolRegistry] = None):
        """
        初始化搜索代理。

        Args:
            llm: Doubao LLM 客户端
            tools: 工具注册表
        """
        self.llm = llm or DoubaoLLM()
        self.tools = tools or ToolRegistry()
        self.messages: List[Dict[str, Any]] = []
        self.iteration_count = 0
        self.start_time = 0.0

        log.info("[搜索代理] 初始化完成")

    def run(self, user_query: str) -> str:
        """
        执行搜索代理的主循环。

        Args:
            user_query: 用户的问题

        Returns:
            代理的最终答案
        """
        self.start_time = time.time()
        self.iteration_count = 0

        log.info("=" * 60)
        log.info(f"[搜索代理] 🚀 开始处理用户问题: {user_query}")
        log.info("=" * 60)

        # 初始化对话
        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_query}
        ]

        # ---- ReAct 主循环 ----
        for iteration in range(MAX_SEARCH_ITERATIONS):
            self.iteration_count = iteration + 1
            log.info(f"\n{'─' * 40}")
            log.info(f"[搜索代理] 🔄 第 {self.iteration_count}/{MAX_SEARCH_ITERATIONS} 轮推理")
            log.info(f"{'─' * 40}")

            # 调用 LLM 进行推理
            response = self.llm.chat(
                messages=self.messages,
                tools=self.tools.get_definitions(),
                tool_choice="auto",
            )

            # 检查是否有工具调用
            if response["tool_calls"]:
                # LLM 决定搜索 → 执行工具
                self._handle_tool_calls(response)

            else:
                # LLM 决定给出最终答案
                log.info(f"[搜索代理] 🎯 LLM 认为信息充足，生成最终答案（共 {self.iteration_count} 轮）")
                answer = response.get("content", "")

                if not answer or len(answer) < 20:
                    # 如果回答太短，强制要求更详细的答案
                    log.warning("[搜索代理] 答案过短，强制要求 LLM 生成详细回答")
                    answer = self.llm.force_final_answer(self.messages)

                elapsed = time.time() - self.start_time
                log.info(f"[搜索代理] ✅ 搜索完成 | 总耗时={elapsed:.1f}s | 总轮次={self.iteration_count}")

                # 记录搜索摘要
                search_summary = self.tools.get_call_summary()
                log.info(f"[搜索代理] 📊 {search_summary}")

                return answer

            # 如果是 error
            if response.get("finish_reason") == "error":
                log.error("[搜索代理] LLM 返回错误，尝试恢复...")
                self.messages.append({
                    "role": "user",
                    "content": "上次调用出现错误。请基于已获得的信息重新尝试，或给出部分答案。"
                })

        # ---- 达到最大迭代次数 ----
        log.warning(f"[搜索代理] ⚠️ 达到最大迭代次数 ({MAX_SEARCH_ITERATIONS})，强制生成答案")
        answer = self.llm.force_final_answer(self.messages)
        elapsed = time.time() - self.start_time
        log.info(f"[搜索代理] ✅ 强制完成 | 总耗时={elapsed:.1f}s | 总轮次={self.iteration_count}")
        return answer

    def _handle_tool_calls(self, response: dict):
        """
        处理 LLM 的工具调用请求。

        将 assistant 的 tool_calls 消息和 tool 的返回结果都追加到对话历史中。

        Args:
            response: LLM 的响应（包含 tool_calls）
        """
        tool_calls = response["tool_calls"]

        # 1. 添加 assistant 消息（包含 tool_calls）
        assistant_message = {
            "role": "assistant",
            "content": response.get("content") or "",  # 思考文本
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"],
                    }
                }
                for tc in tool_calls
            ]
        }
        self.messages.append(assistant_message)

        # 2. 执行每个工具调用并添加 tool 消息
        for tc in tool_calls:
            tool_name = tc["function"]["name"]
            try:
                arguments = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                arguments = {"query": tc["function"]["arguments"]}

            # 执行工具
            result = self.tools.execute(tool_name, arguments)

            # 截断过长的结果，避免超出 token 限制
            if len(result) > 4000:
                result = result[:4000] + "\n\n... [结果已截断，原始长度: {} 字符]".format(len(result))
                log.warning(f"[搜索代理] 搜索结果过长({len(result)}字符)，已截断至4000字符")

            # 添加 tool 返回消息
            tool_message = {
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            }
            self.messages.append(tool_message)

    def get_session_stats(self) -> str:
        """获取当前会话的统计信息"""
        elapsed = time.time() - self.start_time if self.start_time else 0
        lines = [
            "=" * 40,
            "会话统计",
            "=" * 40,
            f"  搜索轮次: {self.iteration_count}",
            f"  总耗时: {elapsed:.1f} 秒",
            f"  消息条数: {len(self.messages)}",
            f"",
            self.tools.get_call_summary(),
        ]
        return "\n".join(lines)
