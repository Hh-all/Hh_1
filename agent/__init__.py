"""
============================================================
智能代理模块 - 统一导出（懒加载）
Agent Package
============================================================

核心模块需要 openai 包，使用懒加载避免导入失败。
"""
_DoubaoLLM = None
_ToolRegistry = None
_SearchAgent = None


def __getattr__(name):
    global _DoubaoLLM, _ToolRegistry, _SearchAgent
    if name == "DoubaoLLM":
        if _DoubaoLLM is None:
            from .llm import DoubaoLLM as DL
            _DoubaoLLM = DL
        return _DoubaoLLM
    if name == "ToolRegistry":
        if _ToolRegistry is None:
            from .tools import ToolRegistry as TR
            _ToolRegistry = TR
        return _ToolRegistry
    if name == "SearchAgent":
        if _SearchAgent is None:
            from .core import SearchAgent as SA
            _SearchAgent = SA
        return _SearchAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["DoubaoLLM", "ToolRegistry", "SearchAgent"]
