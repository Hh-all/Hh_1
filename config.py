"""
============================================================
系统配置 - 所有可配置项集中管理
System Configuration for Agentic Search
============================================================
"""
import os
from pathlib import Path

# 尝试加载 .env 文件（如果 python-dotenv 已安装）
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv 未安装，直接使用系统环境变量

# ---- 项目路径 ----
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
DOCUMENTS_DIR = DATA_DIR / "documents"
CODE_SAMPLES_DIR = DATA_DIR / "code_samples"
LOGS_DIR = PROJECT_ROOT / "logs"
DB_PATH = DATA_DIR / "local.db"
VECTOR_DB_PATH = DATA_DIR / "vector_db"
KEYWORD_INDEX_PATH = DATA_DIR / "keyword_index"

# 确保目录存在
for d in [DATA_DIR, DOCUMENTS_DIR, CODE_SAMPLES_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ---- Doubao (豆包) 模型配置 ----
DOUBAO_API_KEY = os.getenv("DOUBAO_API_KEY", "your-api-key-here")
DOUBAO_BASE_URL = os.getenv("DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
DOUBAO_MODEL = os.getenv("DOUBAO_MODEL", "doubao-pro-32k")  # 推荐: doubao-pro-32k

# ---- 搜索代理配置 ----
MAX_SEARCH_ITERATIONS = int(os.getenv("MAX_SEARCH_ITERATIONS", "10"))  # 最大搜索轮次
SEARCH_TIMEOUT_SECONDS = int(os.getenv("SEARCH_TIMEOUT_SECONDS", "30"))  # 单次搜索超时

# ---- 向量数据库配置 ----
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
VECTOR_DB_COLLECTION = os.getenv("VECTOR_DB_COLLECTION", "enterprise_docs")
TOP_K_VECTOR = int(os.getenv("TOP_K_VECTOR", "5"))

# ---- 关键词搜索配置 ----
TOP_K_KEYWORD = int(os.getenv("TOP_K_KEYWORD", "10"))

# ---- 数据库配置 ----
DB_TOP_N = int(os.getenv("DB_TOP_N", "20"))

# ---- 代码仓库配置 ----
CODE_REPO_PATH = os.getenv("CODE_REPO_PATH", str(CODE_SAMPLES_DIR))
MAX_CODE_RESULTS = int(os.getenv("MAX_CODE_RESULTS", "15"))

# ---- 日志配置 ----
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = LOGS_DIR / "agent.log"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5
