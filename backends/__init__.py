"""
============================================================
搜索后端模块 - 统一导出（懒加载）
Search Backends Package
============================================================
"""
from .database import LocalDatabase
from .code_repo import CodeRepository
from .enterprise_sdk import EnterpriseSDK

# 以下后端需要额外依赖，使用懒加载
# - VectorDatabase: 需要 chromadb, sentence-transformers
# - KeywordSearchEngine: 需要 whoosh, jieba

_VectorDatabase = None
_KeywordSearchEngine = None


def __getattr__(name):
    global _VectorDatabase, _KeywordSearchEngine
    if name == "VectorDatabase":
        if _VectorDatabase is None:
            from .vector_db import VectorDatabase as VD
            _VectorDatabase = VD
        return _VectorDatabase
    if name == "KeywordSearchEngine":
        if _KeywordSearchEngine is None:
            from .keyword_search import KeywordSearchEngine as KSE
            _KeywordSearchEngine = KSE
        return _KeywordSearchEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "LocalDatabase",
    "VectorDatabase",
    "KeywordSearchEngine",
    "CodeRepository",
    "EnterpriseSDK",
]
