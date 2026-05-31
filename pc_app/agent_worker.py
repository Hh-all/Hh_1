"""
后台搜索工作线程 - 在 QThread 中运行 SearchAgent
Background Worker Thread for Running the Search Agent
"""
from PySide6.QtCore import QThread, Signal
from agent.core import SearchAgent
from logger_setup import log


class AgentWorker(QThread):
    """
    在后台线程中运行 SearchAgent，通过信号通知 UI 更新。

    Signals:
        thinking: LLM 正在思考 / 生成了文本
        tool_call: LLM 决定调用某个工具 (tool_name, query)
        tool_result: 工具返回结果 (tool_name, result_preview, elapsed)
        answer_ready: 最终答案就绪 (answer_text)
        finished: 搜索完成 (session_stats)
        error: 发生错误 (error_message)
    """

    thinking = Signal(str)           # LLM 思考文本
    tool_call = Signal(str, str)     # (tool_name, query)
    tool_result = Signal(str, str, str)  # (tool_name, preview, elapsed)
    answer_ready = Signal(str)       # 最终答案
    finished = Signal(str)           # 会话统计
    error = Signal(str)              # 错误信息

    def __init__(self, user_query: str):
        super().__init__()
        self.user_query = user_query

    def run(self):
        """在后台线程中执行搜索代理"""
        try:
            agent = SearchAgent()

            # 通过日志回调捕获实时事件
            self._patch_tools_for_signals(agent)

            answer = agent.run(self.user_query)

            if answer and len(answer) > 20 and not answer.startswith("[LLM"):
                self.answer_ready.emit(answer)
            else:
                self.error.emit(f"搜索未返回有效结果: {answer}")

            stats = agent.get_session_stats()
            self.finished.emit(stats)

        except Exception as e:
            log.error(f"[AgentWorker] 搜索失败: {e}")
            self.error.emit(str(e))

    def _patch_tools_for_signals(self, agent):
        """给工具注册表打补丁，拦截工具调用来发送信号"""
        original_execute = agent.tools.execute

        def patched_execute(tool_name, arguments):
            query = arguments.get("query", str(arguments))
            self.tool_call.emit(tool_name, query[:150])
            result = original_execute(tool_name, arguments)
            preview = result[:300] + ("..." if len(result) > 300 else "")
            self.tool_result.emit(tool_name, preview, "")
            return result

        agent.tools.execute = patched_execute
