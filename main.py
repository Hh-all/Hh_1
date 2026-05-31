"""
============================================================
智能搜索代理 - CLI 入口
Agentic Search System - Command Line Interface
============================================================

使用方法:
    # 初始化数据（首次运行）
    python main.py --seed

    # 交互式搜索
    python main.py

    # 单次查询
    python main.py --query "技术部有哪些员工？"

    # 查看系统状态
    python main.py --status
"""
import sys
import argparse
from pathlib import Path

# 确保项目路径在 sys.path 中
sys.path.insert(0, str(Path(__file__).parent))

from config import *
from logger_setup import log
from agent.core import SearchAgent


def print_banner():
    """打印欢迎横幅"""
    banner = """
╔══════════════════════════════════════════════════════════╗
║        🔍 企业级智能搜索代理系统 v1.0                      ║
║        Agentic Search System with Doubao Reasoning       ║
║                                                          ║
║  搜索后端: SQLite | ChromaDB | Whoosh | CodeRepo | SDK  ║
║  推理引擎: 豆包 (Doubao) via Volcengine Ark               ║
╚══════════════════════════════════════════════════════════╝
"""
    print(banner)


def cmd_seed():
    """初始化数据"""
    from seed_data import main as seed_main
    seed_main()


def cmd_status():
    """显示系统状态"""
    from backends.database import LocalDatabase
    from backends.vector_db import VectorDatabase
    from backends.keyword_search import KeywordSearchEngine
    from backends.code_repo import CodeRepository
    from backends.enterprise_sdk import EnterpriseSDK

    print("\n" + "=" * 50)
    print("📊 系统状态")
    print("=" * 50)

    # 数据库
    try:
        db = LocalDatabase()
        print(f"\n{db.get_schema_info()}")
        db.close()
    except Exception as e:
        print(f"  [数据库] 错误: {e}")

    # 向量DB
    try:
        vdb = VectorDatabase()
        print(f"\n{vdb.get_stats()}")
    except Exception as e:
        print(f"  [向量数据库] 错误: {e}")

    # 关键词搜索
    try:
        kw = KeywordSearchEngine()
        print(f"\n{kw.get_stats()}")
    except Exception as e:
        print(f"  [关键词搜索] 错误: {e}")

    # 代码仓库
    try:
        cr = CodeRepository()
        print(f"\n{cr.get_stats()}")
    except Exception as e:
        print(f"  [代码仓库] 错误: {e}")

    # 企业SDK
    try:
        esdk = EnterpriseSDK()
        print(f"\n[企业SDK] 子系统: HR, CRM, ERP, 知识库 - 全部就绪")
    except Exception as e:
        print(f"  [企业SDK] 错误: {e}")

    print("\n" + "=" * 50)
    print(f"  Doubao模型: {DOUBAO_MODEL}")
    print(f"  API地址: {DOUBAO_BASE_URL}")
    print(f"  最大搜索轮次: {MAX_SEARCH_ITERATIONS}")
    print("=" * 50)


def cmd_query(query: str):
    """单次查询模式"""
    print_banner()
    print(f"\n❓ 用户问题: {query}\n")

    agent = SearchAgent()
    answer = agent.run(query)

    print("\n" + "=" * 60)
    print("📝 最终答案:")
    print("=" * 60)
    print(answer)
    print("\n" + "=" * 60)
    print(agent.get_session_stats())


def cmd_interactive():
    """交互式对话模式"""
    print_banner()

    # 检查 API Key
    if DOUBAO_API_KEY == "your-api-key-here":
        print("\n⚠️  警告: 未设置 DOUBAO_API_KEY！")
        print("请创建 .env 文件并设置: DOUBAO_API_KEY=你的API密钥")
        print("获取API密钥: https://console.volcengine.com/ark\n")

    print("初始化搜索代理...")
    agent = SearchAgent()

    print("\n💡 提示:")
    print("  - 输入问题开始搜索")
    print("  - 输入 /status 查看系统状态")
    print("  - 输入 /history 查看工具调用历史")
    print("  - 输入 /stats 查看当前会话统计")
    print("  - 输入 /quit 或 Ctrl+C 退出\n")

    while True:
        try:
            user_input = input("\n🔍 请输入你的问题: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 再见！")
            break

        if not user_input:
            continue

        # 处理命令
        if user_input.startswith("/"):
            cmd = user_input.lower()
            if cmd in ("/quit", "/exit", "/q"):
                print("👋 再见！")
                break
            elif cmd == "/status":
                cmd_status()
                continue
            elif cmd == "/history":
                print(agent.tools.get_call_summary())
                continue
            elif cmd == "/stats":
                print(agent.get_session_stats())
                continue
            elif cmd == "/help":
                print("可用命令: /status, /history, /stats, /quit, /help")
                continue
            else:
                print(f"未知命令: {user_input}")
                continue

        # 执行搜索
        print(f"\n⏳ 正在搜索: {user_input}\n")
        answer = agent.run(user_input)

        print("\n" + "=" * 60)
        print("📝 最终答案:")
        print("=" * 60)
        print(answer)
        print("\n" + agent.tools.get_call_summary())


def cmd_desktop():
    """启动桌面应用"""
    from pc_app.main import main as desktop_main
    desktop_main()


def main():
    parser = argparse.ArgumentParser(
        description="企业级智能搜索代理系统 - 基于Doubao模型的多源搜索",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --seed              # 初始化所有数据
  python main.py                     # 进入交互模式 (CLI)
  python main.py --desktop           # 启动桌面应用 (GUI)
  python main.py -q "技术部有哪些人"  # 单次查询
  python main.py --status            # 查看系统状态
        """
    )
    parser.add_argument("--seed", "-s", action="store_true", help="初始化/重置所有示例数据")
    parser.add_argument("--query", "-q", type=str, help="单次查询模式")
    parser.add_argument("--desktop", "-d", action="store_true", help="启动桌面应用 (GUI)")
    parser.add_argument("--status", action="store_true", help="查看系统状态")
    parser.add_argument("--model", "-m", type=str, help=f"指定模型 (默认: {DOUBAO_MODEL})")

    args = parser.parse_args()

    # 覆盖模型配置
    if args.model:
        import config
        config.DOUBAO_MODEL = args.model
        log.info(f"使用模型: {args.model}")

    if args.seed:
        cmd_seed()
    elif args.desktop:
        cmd_desktop()
    elif args.status:
        cmd_status()
    elif args.query:
        cmd_query(args.query)
    else:
        cmd_interactive()


if __name__ == "__main__":
    main()
