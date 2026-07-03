"""
============================================================
Doubao (豆包) 大模型集成层
LLM Integration Layer using OpenAI-compatible API
============================================================

通过 Volcengine Ark API 调用豆包模型。
Ark API 与 OpenAI API 兼容，使用 openai 库即可。
"""
import json
import time
from typing import Optional, List, Dict, Any

from openai import OpenAI

from config import DOUBAO_API_KEY, DOUBAO_BASE_URL, DOUBAO_MODEL, SEARCH_TIMEOUT_SECONDS
from logger_setup import log


class DoubaoLLM:
    """
    豆包大模型客户端。

    封装了 Volcengine Ark API 的调用逻辑，
    支持 Function Calling（工具调用）。
    """

    def __init__(self):
        log.info(f"[Doubao LLM] 初始化: model={DOUBAO_MODEL}, base_url={DOUBAO_BASE_URL}")

        if DOUBAO_API_KEY == "your-api-key-here":
            log.warning("[Doubao LLM] ⚠️  未设置 DOUBAO_API_KEY！请在 .env 文件中配置 API Key。")

        self.client = OpenAI(
            api_key=DOUBAO_API_KEY,
            base_url=DOUBAO_BASE_URL,
            timeout=SEARCH_TIMEOUT_SECONDS,
        )
        self.model = DOUBAO_MODEL

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[dict]] = None,
        tool_choice: str = "auto",
    ) -> dict:
        """
        调用豆包模型进行对话。

        Args:
            messages: 对话消息列表
            tools: 可用的工具定义列表（OpenAI function calling 格式）
            tool_choice: 工具选择策略 ("auto" | "none" | "required" | 具体工具)

        Returns:
            {
                "role": "assistant",
                "content": str | None,          # 文本回复
                "tool_calls": list | None,      # 工具调用列表
                "finish_reason": str,
                "usage": dict,
                "raw": ...                      # 原始响应
            }
        """
        log.debug(f"[Doubao LLM] 发送请求，消息数={len(messages)}, 工具数={len(tools) if tools else 0}")

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,  # 低温度以获得更稳定的推理
            "max_tokens": 4096,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        try:
            start_time = time.time()
            response = self.client.chat.completions.create(**kwargs)
            elapsed = time.time() - start_time

            choice = response.choices[0]
            message = choice.message

            result = {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": None,
                "finish_reason": choice.finish_reason,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                "raw": response,
            }

            # 处理工具调用
            if message.tool_calls:
                result["tool_calls"] = []
                for tc in message.tool_calls:
                    tool_call = {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    }
                    result["tool_calls"].append(tool_call)
                    log.info(f"[Doubao LLM] [工具调用] 决定调用工具: {tc.function.name}")

            log.info(
                f"[Doubao LLM] [完成] 响应完成 | "
                f"耗时={elapsed:.2f}s | "
                f"tokens={result['usage']['total_tokens']} | "
                f"finish={result['finish_reason']} | "
                f"has_tool_calls={result['tool_calls'] is not None}"
            )

            if result["content"]:
                log.debug(f"[Doubao LLM] [思考] 思考: {result['content'][:200]}...")

            return result

        except Exception as e:
            log.error(f"[Doubao LLM] [错误] API 调用失败: {e}")
            # 返回模拟的错误响应
            return {
                "role": "assistant",
                "content": f"[LLM调用失败: {e}]",
                "tool_calls": None,
                "finish_reason": "error",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "raw": None,
            }

    def force_final_answer(self, messages: List[Dict[str, Any]]) -> str:
        """
        强制模型基于已有信息给出最终答案。
        不使用工具调用，只生成文本回复。

        Args:
            messages: 完整的对话历史

        Returns:
            最终答案文本
        """
        log.info("[Doubao LLM] [生成] 强制生成最终答案...")

        # 追加最终指令
        final_messages = messages + [{
            "role": "user",
            "content": (
                "你已经收集了足够的信息。请基于以上所有搜索结果，"
                "给用户一个完整、准确、有条理的回答。\n\n"
                "要求：\n"
                "1. 综合所有搜索到的信息\n"
                "2. 给出具体的数据和事实\n"
                "3. 如果信息有冲突，指出差异\n"
                "4. 如果某些信息确实找不到，诚实说明\n"
                "5. 用清晰的结构组织答案"
            )
        }]

        result = self.chat(final_messages, tools=None)  # 不传 tools，强制文本回复
        return result.get("content", "抱歉，无法生成回答。")
