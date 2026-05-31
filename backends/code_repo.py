"""
============================================================
本地代码仓库搜索 - 源代码检索
Local Code Repository Search with Grep & Structured Analysis
============================================================
"""
import os
import re
import fnmatch
from pathlib import Path
from typing import Optional, List

from config import CODE_REPO_PATH, MAX_CODE_RESULTS
from logger_setup import log


class CodeRepository:
    """
    本地代码仓库搜索后端。

    支持：
    - 按文件名查找
    - 按内容（grep）搜索
    - 按函数/类定义搜索
    - 文件列表浏览
    """

    # 支持的代码文件扩展名
    CODE_EXTENSIONS = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs",
        ".c", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".swift",
        ".kt", ".scala", ".sql", ".sh", ".bash", ".yaml", ".yml",
        ".json", ".xml", ".toml", ".ini", ".cfg", ".md", ".txt"
    }

    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = Path(repo_path or CODE_REPO_PATH)
        log.info(f"[代码仓库] 代码仓库路径: {self.repo_path}")

    def search(self, query: str, max_results: int = MAX_CODE_RESULTS) -> str:
        """
        智能代码搜索。
        根据 query 类型自动选择搜索策略：
        - "file:xxx" → 按文件名搜索
        - "func:xxx" / "def xxx" → 按函数/类定义搜索
        - 其他 → 按内容 grep 搜索

        Args:
            query: 搜索查询
            max_results: 最大结果数

        Returns:
            格式化的搜索结果
        """
        log.info(f"[代码仓库] 代码搜索: {query[:100]}...")

        query_lower = query.lower().strip()

        # 按文件名搜索
        if query_lower.startswith("file:") or query_lower.startswith("文件名:"):
            pattern = query.split(":", 1)[1].strip()
            return self._search_by_filename(pattern, max_results)

        # 按函数/类定义搜索
        if query_lower.startswith("func:") or query_lower.startswith("def ") or \
           query_lower.startswith("class ") or query_lower.startswith("函数:") or \
           query_lower.startswith("类:"):
            pattern = re.sub(r'^(func:|函数:|def |class |类:)\s*', '', query, flags=re.IGNORECASE)
            return self._search_definitions(pattern, max_results)

        # 按文件列表
        if query_lower in ("list", "ls", "列表", "文件列表", "dir"):
            return self._list_files()

        # 默认：按内容搜索
        return self._grep_content(query, max_results)

    def _search_by_filename(self, pattern: str, max_results: int) -> str:
        """按文件名模式搜索"""
        results = []
        for root, dirs, files in os.walk(self.repo_path):
            # 跳过隐藏目录和常见的非代码目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in
                       ('node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build')]

            for filename in files:
                if fnmatch.fnmatch(filename, f"*{pattern}*"):
                    filepath = Path(root) / filename
                    rel_path = filepath.relative_to(self.repo_path)
                    try:
                        size = filepath.stat().st_size
                        lines = self._count_lines(filepath)
                        results.append(f"  {rel_path} ({lines} 行, {size:,} bytes)")
                    except OSError:
                        results.append(f"  {rel_path}")

                if len(results) >= max_results:
                    break
            if len(results) >= max_results:
                break

        if not results:
            return f"未找到匹配文件名 '*{pattern}*' 的文件。"

        return f"文件名搜索 '{pattern}' 结果（共 {len(results)} 个文件）:\n" + "\n".join(results)

    def _search_definitions(self, pattern: str, max_results: int) -> str:
        """搜索函数和类定义"""
        results = []
        # 匹配多种语言的函数/类定义
        def_patterns = [
            # Python
            (r'^\s*(def|class)\s+(\w*' + re.escape(pattern) + r'\w*)', '.py'),
            # JavaScript/TypeScript
            (r'(function\s+(\w*' + re.escape(pattern) + r'\w*)|(\w*' + re.escape(pattern) + r'\w*)\s*[=:]\s*(function|\(.*\)\s*=>|class))', '.js,.ts,.jsx,.tsx'),
            # Java
            (r'(public|private|protected|static|\s)+[\w<>\[\]]+\s+(\w*' + re.escape(pattern) + r'\w*)\s*\(', '.java'),
            # Go
            (r'func\s+(\(\w+\s+\*?\w+\)\s+)?(\w*' + re.escape(pattern) + r'\w*)\s*\(', '.go'),
            # C/C++
            (r'^\s*[\w\[\]*&]+\s+(\w*' + re.escape(pattern) + r'\w*)\s*\([^)]*\)\s*\{', '.c,.cpp,.h,.hpp'),
        ]

        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in
                       ('node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build')]

            for filename in files:
                filepath = Path(root) / filename
                ext = filepath.suffix

                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_no, line in enumerate(f, 1):
                            matched = False
                            for regex, exts in def_patterns:
                                if ext in exts.split(','):
                                    if re.search(regex, line, re.IGNORECASE):
                                        matched = True
                                        break
                            if matched:
                                rel_path = filepath.relative_to(self.repo_path)
                                results.append(f"  {rel_path}:{line_no}  {line.rstrip()[:120]}")
                except Exception:
                    continue

                if len(results) >= max_results:
                    break
            if len(results) >= max_results:
                break

        if not results:
            return f"未找到匹配 '{pattern}' 的函数/类定义。"

        return f"定义搜索 '{pattern}' 结果（共 {len(results)} 个匹配）:\n" + "\n".join(results)

    def _grep_content(self, query: str, max_results: int) -> str:
        """按文件内容搜索（类似 grep）"""
        results = []
        # 将中文查询分词，支持多关键词
        keywords = query.split()

        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in
                       ('node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build')]

            for filename in files:
                if Path(filename).suffix not in self.CODE_EXTENSIONS:
                    continue

                filepath = Path(root) / filename
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_no, line in enumerate(f, 1):
                            # 所有关键词都要匹配（AND 逻辑）
                            if all(kw.lower() in line.lower() for kw in keywords):
                                rel_path = filepath.relative_to(self.repo_path)
                                results.append(f"  {rel_path}:{line_no}  {line.rstrip()[:150]}")
                except Exception:
                    continue

                if len(results) >= max_results:
                    break
            if len(results) >= max_results:
                break

        if not results:
            # 尝试用 OR 逻辑重新搜索
            return self._grep_content_or(query, max_results)

        return f"代码内容搜索 '{query}' 结果（共 {len(results)} 个匹配）:\n" + "\n".join(results)

    def _grep_content_or(self, query: str, max_results: int) -> str:
        """OR 逻辑的 grep 搜索（宽松模式）"""
        results = []
        keywords = query.split()

        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in
                       ('node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build')]

            for filename in files:
                if Path(filename).suffix not in self.CODE_EXTENSIONS:
                    continue

                filepath = Path(root) / filename
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_no, line in enumerate(f, 1):
                            if any(kw.lower() in line.lower() for kw in keywords):
                                rel_path = filepath.relative_to(self.repo_path)
                                results.append(f"  {rel_path}:{line_no}  {line.rstrip()[:150]}")
                except Exception:
                    continue

                if len(results) >= max_results:
                    break
            if len(results) >= max_results:
                break

        if not results:
            return f"未找到包含 '{query}' 的代码行。"

        return f"代码内容搜索 '{query}'（宽松模式）结果:\n" + "\n".join(results)

    def _list_files(self) -> str:
        """列出代码仓库中的文件"""
        lines = ["代码仓库文件列表:"]
        count = 0
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in
                       ('node_modules', '__pycache__', 'venv', '.venv')]
            rel_root = Path(root).relative_to(self.repo_path)
            if str(rel_root) != '.':
                lines.append(f"\n  [{rel_root}/]")

            for fname in sorted(files)[:20]:
                if Path(fname).suffix in self.CODE_EXTENSIONS:
                    lines.append(f"    {fname}")
                    count += 1

            if count > 50:
                lines.append(f"  ... 还有更多文件（超过50个，请使用更具体的搜索）")
                break

        return "\n".join(lines)

    def get_stats(self) -> str:
        """获取代码仓库统计"""
        total_files = 0
        total_lines = 0
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in
                       ('node_modules', '__pycache__', 'venv', '.venv')]
            for f in files:
                if Path(f).suffix in self.CODE_EXTENSIONS:
                    total_files += 1
                    try:
                        total_lines += self._count_lines(Path(root) / f)
                    except Exception:
                        pass

        return f"代码仓库状态: 路径='{self.repo_path}', 文件数={total_files}, 总行数≈{total_lines:,}"

    @staticmethod
    def _count_lines(filepath: Path) -> int:
        """统计文件行数"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                return sum(1 for _ in f)
        except Exception:
            return 0
