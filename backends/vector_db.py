"""
============================================================
本地向量数据库 (ChromaDB) - 语义相似度搜索
Local Vector Database Backend for Semantic Search

嵌入策略（按优先级自动选择）：
  1. Doubao 文本嵌入 API（需要开通 doubao-embedding-text-xxx）
  2. 本地 TF-IDF 向量化（scikit-learn，纯本地，无需联网）
  3. 本地 sentence-transformers 模型（需要能访问 HuggingFace）
============================================================
"""
import json
import pickle
from pathlib import Path
from typing import Optional, List

import chromadb
from chromadb.config import Settings as ChromaSettings

from config import (
    VECTOR_DB_PATH, VECTOR_DB_COLLECTION, EMBEDDING_MODEL, TOP_K_VECTOR,
    DOUBAO_API_KEY, DOUBAO_BASE_URL,
)
from logger_setup import log

# Doubao 嵌入模型名称（文本嵌入，非Vision）
DOUBAO_EMBEDDING_MODEL = "doubao-embedding-text-240715"
TFIDF_VOCAB_SIZE = 5000
TFIDF_CACHE_FILE = VECTOR_DB_PATH / "tfidf_vectorizer.pkl"


class VectorDatabase:
    """
    本地向量数据库后端。

    使用 ChromaDB 做存储 + Doubao API / 本地模型做嵌入，
    对文档进行语义级别的相似度搜索。
    """

    def __init__(self, persist_path: Optional[Path] = None):
        self.persist_path = str(persist_path or VECTOR_DB_PATH)
        self.collection_name = VECTOR_DB_COLLECTION

        # 嵌入函数（延迟加载）
        self._embed_fn = None
        self._embed_mode = None  # "api" or "local"

        # 初始化 ChromaDB 客户端
        self.client = chromadb.PersistentClient(
            path=self.persist_path,
            settings=ChromaSettings(anonymized_telemetry=False)
        )

        # 获取或创建 collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

        doc_count = self.collection.count()
        log.info(f"[向量数据库] 已连接，collection='{self.collection_name}', 文档数={doc_count}")

    # ================================================================
    # 嵌入函数：优先使用 Doubao API，回退到本地模型
    # ================================================================

    def _init_embed_fn(self):
        """初始化嵌入函数（延迟加载）"""
        if self._embed_fn is not None:
            return

        # 方案1: 使用 Doubao 嵌入 API（国内网络友好）
        if DOUBAO_API_KEY and DOUBAO_API_KEY != "your-api-key-here":
            if self._try_init_api_embedding():
                return

        # 方案2: 回退到本地模型（需要能访问 HuggingFace）
        self._try_init_local_embedding()

    def _try_init_api_embedding(self) -> bool:
        """尝试使用 Doubao 嵌入 API"""
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=DOUBAO_API_KEY,
                base_url=DOUBAO_BASE_URL,
                timeout=30,
            )

            # 测试 API 是否可用
            test_response = client.embeddings.create(
                model=DOUBAO_EMBEDDING_MODEL,
                input=["测试"],
                encoding_format="float",
            )
            test_dim = len(test_response.data[0].embedding)
            log.info(f"[向量数据库] ✅ 使用 Doubao 嵌入 API | 模型={DOUBAO_EMBEDDING_MODEL} | 维度={test_dim}")

            def api_embed(texts: List[str]) -> List[List[float]]:
                """批量调用 Doubao 嵌入 API"""
                if not texts:
                    return []
                # 分批处理，避免单次请求过大
                batch_size = 20
                all_embeddings = []
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    resp = client.embeddings.create(
                        model=DOUBAO_EMBEDDING_MODEL,
                        input=batch,
                        encoding_format="float",
                    )
                    all_embeddings.extend([d.embedding for d in resp.data])
                return all_embeddings

            self._embed_fn = api_embed
            self._embed_mode = "api"
            return True

        except Exception as e:
            log.warning(f"[向量数据库] Doubao 嵌入 API 不可用: {e}")
            return False

    def _try_init_local_embedding(self):
        """回退：使用本地 TF-IDF 向量化"""
        # 方案2: TF-IDF（scikit-learn，纯本地）
        if self._try_init_tfidf_embedding():
            return

        # 方案3: sentence-transformers（需要 HuggingFace）
        if self._try_init_sentence_transformers():
            return

        raise RuntimeError(
            "无法初始化嵌入函数。请检查：\n"
            "1. Doubao API Key 是否已开通文本嵌入模型\n"
            "2. 网络是否能访问火山引擎 API\n"
            "3. 或安装: pip install scikit-learn"
        )

    def _try_init_tfidf_embedding(self) -> bool:
        """使用本地 TF-IDF 进行文本向量化（无需API，无需联网）"""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            import jieba

            log.info("[向量数据库] 使用本地 TF-IDF 向量化 (scikit-learn + jieba)")

            # 尝试加载已保存的 vectorizer
            if TFIDF_CACHE_FILE.exists():
                with open(TFIDF_CACHE_FILE, 'rb') as f:
                    vectorizer = pickle.load(f)
                log.info(f"[向量数据库] 已加载 TF-IDF vectorizer (词汇量={len(vectorizer.vocabulary_)})")
            else:
                vectorizer = None

            def tfidf_embed(texts: List[str]) -> List[List[float]]:
                nonlocal vectorizer
                # 用 jieba 分词预处理文本
                processed = [" ".join(jieba.cut(t)) for t in texts]

                if vectorizer is None:
                    vectorizer = TfidfVectorizer(max_features=TFIDF_VOCAB_SIZE)
                    tfidf_matrix = vectorizer.fit_transform(processed)
                    # 保存 vectorizer
                    TFIDF_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                    with open(TFIDF_CACHE_FILE, 'wb') as f:
                        pickle.dump(vectorizer, f)
                    log.info(f"[向量数据库] 训练并保存 TF-IDF vectorizer (词汇量={len(vectorizer.vocabulary_)})")
                else:
                    tfidf_matrix = vectorizer.transform(processed)

                return tfidf_matrix.toarray().tolist()

            self._embed_fn = tfidf_embed
            self._embed_mode = "tfidf"
            return True

        except ImportError as e:
            log.warning(f"[向量数据库] scikit-learn/jieba 不可用: {e}")
            return False
        except Exception as e:
            log.warning(f"[向量数据库] TF-IDF 初始化失败: {e}")
            return False

    def _try_init_sentence_transformers(self) -> bool:
        """回退：使用本地 sentence-transformers 模型"""
        try:
            from sentence_transformers import SentenceTransformer
            log.info(f"[向量数据库] 正在加载本地 embedding 模型: {EMBEDDING_MODEL}...")
            model = SentenceTransformer(EMBEDDING_MODEL)
            log.info(f"[向量数据库] ✅ 使用本地 embedding 模型 | 模型={EMBEDDING_MODEL}")
            self._embed_fn = lambda texts: model.encode(texts).tolist()
            self._embed_mode = "local"
            return True
        except Exception as e:
            log.warning(f"[向量数据库] 本地模型不可用: {e}")
            return False

    # ================================================================
    # 公共接口
    # ================================================================

    def search(self, query: str, top_k: int = TOP_K_VECTOR) -> str:
        """
        语义搜索：将 query 向量化，在 ChromaDB 中查找最相似的文档。

        Args:
            query: 自然语言搜索查询
            top_k: 返回最相似的 K 个结果

        Returns:
            格式化的搜索结果字符串
        """
        self._init_embed_fn()
        log.info(f"[向量数据库] 语义搜索 (mode={self._embed_mode}): {query[:100]}...")

        if self.collection.count() == 0:
            return "向量数据库中没有文档。请先添加文档（运行 python main.py --seed 初始化数据）。"

        try:
            query_embedding = self._embed_fn([query])[0]
        except Exception as e:
            return f"嵌入查询失败: {e}"

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.collection.count())
        )

        if not results or not results['documents'] or not results['documents'][0]:
            return "未找到语义相似的文档。"

        return self._format_results(results)

    def add_documents(self, documents: List[str], metadatas: Optional[List[dict]] = None,
                      ids: Optional[List[str]] = None):
        """
        向向量数据库添加文档。

        Args:
            documents: 文档文本列表
            metadatas: 文档元数据列表
            ids: 文档 ID 列表
        """
        if not documents:
            return

        self._init_embed_fn()
        log.info(f"[向量数据库] 正在嵌入 {len(documents)} 个文档 (mode={self._embed_mode})...")

        try:
            embeddings = self._embed_fn(documents)
        except Exception as e:
            log.error(f"[向量数据库] 嵌入失败: {e}")
            raise

        if ids is None:
            existing = self.collection.count()
            ids = [f"doc_{existing + i}" for i in range(len(documents))]
        if metadatas is None:
            metadatas = [{} for _ in documents]

        self.collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        log.info(f"[向量数据库] 已添加 {len(documents)} 个文档，当前总数: {self.collection.count()}")

    def get_stats(self) -> str:
        """获取向量数据库统计信息"""
        count = self.collection.count()
        mode_info = f", 嵌入模式={self._embed_mode}" if self._embed_mode else ""
        return f"向量数据库状态: collection='{self.collection_name}', 文档总数={count}{mode_info}"

    # ================================================================
    # 内部方法
    # ================================================================

    def _format_results(self, results: dict) -> str:
        """格式化搜索结果为可读字符串"""
        lines = [f"向量语义搜索结果（共 {len(results['documents'][0])} 条相关性结果）:\n"]

        for i, (doc, meta, dist) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results.get('distances', [[0] * len(results['documents'][0])])[0]
        ), 1):
            similarity = max(0, 1 - dist) if dist else 1.0  # cosine distance → similarity
            source = meta.get('source', '未知来源') if meta else '未知来源'
            title = meta.get('title', '无标题') if meta else '无标题'

            doc_preview = doc[:300] + "..." if len(doc) > 300 else doc

            lines.append(f"[结果 {i}] 相似度: {similarity:.3f} | 来源: {source} | 标题: {title}")
            lines.append(f"{doc_preview}\n")

        return "\n".join(lines)
