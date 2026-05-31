"""
============================================================
本地关键词搜索引擎 (Whoosh) - 全文检索
Local Full-Text Keyword Search with Chinese Tokenization
============================================================
"""
import os
import shutil
from pathlib import Path
from typing import Optional, List

from whoosh import index
from whoosh.fields import Schema, TEXT, ID, KEYWORD, STORED
from whoosh.analysis import SimpleAnalyzer
from whoosh.qparser import MultifieldParser, OrGroup

import jieba

from config import KEYWORD_INDEX_PATH, TOP_K_KEYWORD
from logger_setup import log


def preprocess_chinese(text: str) -> str:
    """
    中文文本预处理：检测中文并用 jieba 分词。
    将中文分词结果用空格连接，英文保持原样。
    """
    if not text:
        return ""
    if any('一' <= c <= '鿿' for c in text):
        tokens = jieba.cut(text)
        return " ".join(t.strip() for t in tokens if t.strip())
    return text


class KeywordSearchEngine:
    """
    本地关键词全文检索引擎。

    基于 Whoosh + jieba 分词，支持中文全文检索。
    通过在索引和搜索时对中文文本做 jieba 分词预处理，
    使标准 Whoosh 分析器能够正确索引中文。
    """

    def __init__(self, index_path: Optional[Path] = None):
        self.index_path = str(index_path or KEYWORD_INDEX_PATH)
        # 使用 SimpleAnalyzer，配合 jieba 预处理
        analyzer = SimpleAnalyzer()
        self.schema = Schema(
            doc_id=ID(stored=True, unique=True),
            title=TEXT(stored=True, analyzer=analyzer),
            content=TEXT(stored=True, analyzer=analyzer),
            source=ID(stored=True),
            tags=KEYWORD(stored=True, commas=True),
        )
        self._ix = None
        self._ensure_index()

    @property
    def ix(self):
        if self._ix is None:
            self._ix = index.open_dir(self.index_path)
        return self._ix

    def _ensure_index(self):
        """确保索引目录存在，不存在则创建"""
        if not os.path.exists(self.index_path):
            os.makedirs(self.index_path, exist_ok=True)
            self._ix = index.create_in(self.index_path, self.schema)
            log.info(f"[关键词搜索] 已创建新索引: {self.index_path}")
        else:
            try:
                self._ix = index.open_dir(self.index_path)
                log.info(f"[关键词搜索] 已打开索引: {self.index_path}")
            except Exception:
                # 索引损坏，重建
                shutil.rmtree(self.index_path)
                os.makedirs(self.index_path, exist_ok=True)
                self._ix = index.create_in(self.index_path, self.schema)
                log.info(f"[关键词搜索] 索引重建: {self.index_path}")

    def search(self, query: str, top_k: int = TOP_K_KEYWORD) -> str:
        """
        全文关键词搜索。

        Args:
            query: 搜索关键词/短语
            top_k: 返回结果数量

        Returns:
            格式化的搜索结果
        """
        # 对中文查询进行分词预处理
        processed_query = preprocess_chinese(query)
        log.info(f"[关键词搜索] 全文检索: {query[:100]}... -> '{processed_query[:100]}'")

        try:
            with self.ix.searcher() as searcher:
                # 多字段搜索（标题 + 内容 + 标签）
                parser = MultifieldParser(
                    ["title", "content", "tags"],
                    schema=self.ix.schema,
                    group=OrGroup
                )

                # 解析查询
                parsed_query = parser.parse(processed_query)

                # 执行搜索
                results = searcher.search(parsed_query, limit=top_k)

                if not results:
                    # 尝试用原始查询重试（英文关键词）
                    if processed_query != query:
                        parsed_query = parser.parse(query)
                        results = searcher.search(parsed_query, limit=top_k)

                    if not results:
                        return f"未找到匹配 '{query}' 的文档。"

                return self._format_results(results)

        except Exception as e:
            log.error(f"[关键词搜索] 搜索错误: {e}")
            # 返回空结果而不是报错
            return f"搜索 '{query}' 时出现问题: {e}"

    def index_documents(self, documents: List[dict]):
        """
        批量索引文档。

        Args:
            documents: 文档字典列表，每个文档包含:
                - doc_id: 唯一标识
                - title: 标题
                - content: 内容
                - source: 来源
                - tags: 标签（逗号分隔的字符串）
        """
        writer = self.ix.writer()
        count = 0

        for doc in documents:
            doc_id = doc.get("doc_id", "")
            # 如果已存在，先删除再更新
            writer.delete_by_term("doc_id", doc_id)

            # 对中文内容做 jieba 分词预处理
            title = preprocess_chinese(doc.get("title", ""))
            content = preprocess_chinese(doc.get("content", ""))
            tags = doc.get("tags", "")

            writer.add_document(
                doc_id=doc_id,
                title=title,
                content=content,
                source=doc.get("source", "unknown"),
                tags=tags,
            )
            count += 1

        writer.commit()
        log.info(f"[关键词搜索] 已索引 {count} 个文档")

    def index_single(self, doc_id: str, title: str, content: str,
                     source: str = "manual", tags: str = ""):
        """索引单个文档"""
        self.index_documents([{
            "doc_id": doc_id,
            "title": title,
            "content": content,
            "source": source,
            "tags": tags
        }])

    def get_stats(self) -> str:
        """获取索引统计信息"""
        try:
            with self.ix.searcher() as searcher:
                doc_count = searcher.doc_count_all()
        except Exception:
            doc_count = 0
        return f"关键词搜索索引状态: 路径='{self.index_path}', 文档总数={doc_count}"

    def rebuild_index(self):
        """重建索引（清空后重新创建）"""
        if os.path.exists(self.index_path):
            shutil.rmtree(self.index_path)
        self._ensure_index()
        log.info("[关键词搜索] 索引已重建")

    def _format_results(self, results) -> str:
        """格式化搜索结果"""
        lines = [f"关键词搜索结果（共 {len(results)} 条结果）:\n"]

        for i, hit in enumerate(results, 1):
            title = hit.get('title', '无标题')
            source = hit.get('source', '未知来源')
            content_preview = hit.get('content', '')[:250]
            if len(hit.get('content', '')) > 250:
                content_preview += "..."

            lines.append(f"[结果 {i}] 标题: {title} | 来源: {source} | 评分: {hit.score:.2f}")
            lines.append(f"{content_preview}\n")

        return "\n".join(lines)
