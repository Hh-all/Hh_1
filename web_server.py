"""
============================================================
Web 服务 - 将搜索代理部署为内网 HTTP 服务
Web Server for LAN Deployment (Flask + Waitress + SSE)
============================================================

启动后局域网内其他设备可通过浏览器访问：
  http://<本机IP>:8080

API Key 仅存储在服务端 .env 中，不会暴露给客户端。
"""
import json
import os
import queue
import sys
import threading
import time
from pathlib import Path

from flask import Flask, request, jsonify, Response, send_from_directory

# 确保项目根目录可 import
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import DOUBAO_API_KEY, DOUBAO_MODEL, MAX_SEARCH_ITERATIONS
from logger_setup import log
from agent.core import SearchAgent

WEB_UI_DIR = str(PROJECT_ROOT / "web_ui")

app = Flask(__name__, static_folder=WEB_UI_DIR, static_url_path="")

# ---- 并发控制 ----
# Doubao API 最大并发调用数，防止多人同时搜索时触发 API 限流
_DOUBAO_SEMAPHORE = threading.BoundedSemaphore(
    int(os.getenv("MAX_CONCURRENT_DOUBAO", "5"))
)

# 当前活跃搜索计数
_active_searches = 0
_active_searches_lock = threading.Lock()


# ================================================================
# 事件类型定义
# ================================================================

class EventType:
    """SSE 事件类型常量"""
    STATUS = "status"        # 状态更新
    THINKING = "thinking"    # LLM 思考过程
    TOOL_CALL = "tool_call"  # 工具调用
    TOOL_RESULT = "tool_result"  # 工具结果
    ITERATION = "iteration"  # 搜索轮次
    ANSWER = "answer"        # 最终答案
    DONE = "done"            # 搜索完成
    ERROR = "error"          # 错误


# ================================================================
# 搜索执行器 - 在后台线程中运行 SearchAgent
# ================================================================

def _run_search(user_query: str, event_queue: queue.Queue):
    """
    在后台线程中执行搜索代理,通过事件队列实时推送进度。

    Args:
        user_query: 用户问题
        event_queue: 线程安全的事件队列
    """
    # 获取 API 并发许可
    acquired = _DOUBAO_SEMAPHORE.acquire(timeout=60)
    if not acquired:
        event_queue.put({"type": EventType.ERROR, "data": {"text": "系统繁忙，请稍后重试（API 并发已达上限）"}})
        event_queue.put({"type": EventType.DONE, "data": {"stats": ""}})
        return

    # 更新活跃计数
    global _active_searches
    with _active_searches_lock:
        _active_searches += 1

    try:
        agent = SearchAgent()

        # ---- Monkey-patch 拦截实时事件 ----
        original_execute = agent.tools.execute
        original_handle = agent._handle_tool_calls
        captured_thinking: list[str] = []

        def patched_execute(tool_name, arguments):
            query_text = arguments.get("query", str(arguments))
            event_queue.put({"type": EventType.TOOL_CALL, "data": {"tool": tool_name, "query": query_text[:200]}})

            # 发送已捕获的思考文本
            if captured_thinking:
                thinking_text = " ".join(captured_thinking).strip()
                captured_thinking.clear()
                if thinking_text:
                    event_queue.put({"type": EventType.THINKING, "data": {"text": thinking_text}})

            result = original_execute(tool_name, arguments)
            preview = result[:500] + ("..." if len(result) > 500 else "")
            event_queue.put({"type": EventType.TOOL_RESULT, "data": {"tool": tool_name, "preview": preview}})
            return result

        agent.tools.execute = patched_execute

        def patched_handle_tool_calls(response):
            thinking_text = response.get("content", "")
            if thinking_text and len(thinking_text.strip()) > 5:
                captured_thinking.append(thinking_text.strip())

            current = agent.iteration_count
            event_queue.put({
                "type": EventType.ITERATION,
                "data": {"current": current, "maximum": MAX_SEARCH_ITERATIONS}
            })

            return original_handle(response)

        agent._handle_tool_calls = patched_handle_tool_calls

        # ---- 执行搜索 ----
        event_queue.put({"type": EventType.STATUS, "data": {"text": "searching"}})
        answer = agent.run(user_query)

        if answer and len(answer) > 20 and not answer.startswith("[LLM"):
            event_queue.put({"type": EventType.ANSWER, "data": {"text": answer}})
        else:
            event_queue.put({"type": EventType.ERROR, "data": {"text": f"搜索未返回有效结果: {answer}"}})

        stats = agent.get_session_stats()
        event_queue.put({"type": EventType.DONE, "data": {"stats": stats}})

    except Exception as e:
        log.error(f"[WebServer] 搜索线程异常: {e}")
        event_queue.put({"type": EventType.ERROR, "data": {"text": str(e)}})
        event_queue.put({"type": EventType.DONE, "data": {"stats": ""}})

    finally:
        with _active_searches_lock:
            _active_searches -= 1
        _DOUBAO_SEMAPHORE.release()


# ================================================================
# 路由
# ================================================================

@app.route("/")
def index():
    """返回聊天网页"""
    return send_from_directory(WEB_UI_DIR, "index.html")


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """
    搜索接口 - SSE 流式返回结果。

    请求体: {"query": "用户问题"}
    响应: text/event-stream 流
    """
    data = request.get_json(silent=True)
    if not data or "query" not in data:
        return jsonify({"error": "缺少 query 参数"}), 400

    query = data["query"].strip()
    if not query:
        return jsonify({"error": "query 不能为空"}), 400

    # 检查 API Key
    if DOUBAO_API_KEY == "your-api-key-here":
        return jsonify({"error": "服务端未配置 API Key"}), 500

    def generate():
        """SSE 事件生成器"""
        event_queue: queue.Queue = queue.Queue()
        thread = threading.Thread(target=_run_search, args=(query, event_queue), daemon=True)
        thread.start()

        try:
            while True:
                try:
                    event = event_queue.get(timeout=120)  # 最多等 2 分钟
                    data_line = f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    yield data_line

                    if event["type"] in (EventType.DONE, EventType.ERROR):
                        break

                except queue.Empty:
                    yield f"data: {json.dumps({'type': EventType.ERROR, 'data': {'text': '搜索超时'}}, ensure_ascii=False)}\n\n"
                    break
        finally:
            # 确保 SSE 流正确关闭，前端依赖流关闭来重置状态
            yield f"data: {json.dumps({'type': EventType.DONE, 'data': {'stats': ''}}, ensure_ascii=False)}\n\n"
            thread.join(timeout=5)

    return Response(generate(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Access-Control-Allow-Origin": "*",
    })


@app.route("/api/health", methods=["GET"])
def api_health():
    """健康检查接口（含并发状态）"""
    return jsonify({
        "status": "ok",
        "model": DOUBAO_MODEL,
        "api_configured": DOUBAO_API_KEY != "your-api-key-here",
        "active_searches": _active_searches,
        "max_concurrent_api": _DOUBAO_SEMAPHORE._initial_value,
    })


# ================================================================
# 启动入口
# ================================================================

def start_server(host: str = "0.0.0.0", port: int = 8080, debug: bool = False):
    """
    启动 Web 服务器。

    使用 waitress 作为生产级 WSGI 服务器（Windows 兼容），
    支持多线程并发处理。

    Args:
        host: 监听地址,默认 0.0.0.0（允许局域网访问）
        port: 监听端口
        debug: 是否使用 Flask 开发模式（仅本地调试用）
    """
    import socket

    # 获取本机局域网 IP
    local_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    max_api = _DOUBAO_SEMAPHORE._initial_value

    print(f"""
╔══════════════════════════════════════════════════════╗
║     企业智能搜索代理 - Web 服务                       ║
║     Agentic Search Web Server (Waitress)             ║
╠══════════════════════════════════════════════════════╣
║                                                      ║
║  本地访问:   http://127.0.0.1:{port}                   ║
║  局域网访问: http://{local_ip}:{port}                 ║
║                                                      ║
║  API 最大并发: {max_api}                                  ║
║                                                      ║
║  按 Ctrl+C 停止服务                                   ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
""")

    if DOUBAO_API_KEY == "your-api-key-here":
        print("  ⚠️  警告: 未配置 DOUBAO_API_KEY，请在 .env 文件中设置！\n")

    if debug:
        print("  [开发模式] 使用 Flask 内置服务器\n")
        app.run(host=host, port=port, debug=True, threaded=True)
    else:
        try:
            from waitress import serve
            # waitress 线程池：4-16 个工作线程，足够处理内网并发
            threads = int(os.getenv("WAITRESS_THREADS", "8"))
            print(f"  [生产模式] Waitress WSGI 服务器，工作线程={threads}\n")
            serve(app, host=host, port=port, threads=threads)
        except ImportError:
            print("  ⚠️  waitress 未安装，回退到 Flask 开发服务器")
            print("     安装: pip install waitress\n")
            app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    start_server()
