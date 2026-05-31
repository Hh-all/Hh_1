"""
============================================================
本地关系型数据库 (SQLite) - 结构化数据查询
Local SQLite Database Backend for Structured Data
============================================================
"""
import sqlite3
import json
from pathlib import Path
from typing import Optional

from config import DB_PATH, DB_TOP_N
from logger_setup import log


class LocalDatabase:
    """
    本地 SQLite 数据库后端。

    管理结构化的企业数据：员工、部门、项目、销售、库存等。
    支持自然语言查询映射和原始 SQL 执行。
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = str(db_path or DB_PATH)
        self.conn: Optional[sqlite3.Connection] = None
        self._connect()

    def _connect(self):
        """建立数据库连接"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # 让结果可以通过列名访问
        log.info(f"[本地数据库] 已连接: {self.db_path}")

    def close(self):
        if self.conn:
            self.conn.close()
            log.info("[本地数据库] 连接已关闭")

    # ---- 表结构查询 ----
    def get_schema_info(self) -> str:
        """获取数据库的表结构摘要，供 LLM 理解数据结构"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = cursor.fetchall()

        if not tables:
            return "数据库中没有用户表。"

        lines = ["【数据库表结构】"]
        for (table_name,) in tables:
            cursor.execute(f"PRAGMA table_info('{table_name}')")
            columns = cursor.fetchall()
            col_strs = [f"  {col['name']} ({col['type']})" for col in columns]

            cursor.execute(f"SELECT COUNT(*) as cnt FROM '{table_name}'")
            row_count = cursor.fetchone()['cnt']

            lines.append(f"\n表名: {table_name} ({row_count} 行)")
            lines.extend(col_strs)

        return "\n".join(lines)

    # ---- 搜索主入口 ----
    def search(self, query: str, top_n: int = DB_TOP_N) -> str:
        """
        执行数据库搜索。
        如果 query 是 SQL，直接执行；否则进行智能表匹配。

        Args:
            query: SQL 查询语句或自然语言数据请求
            top_n: 返回结果数量上限

        Returns:
            格式化的搜索结果字符串
        """
        log.info(f"[本地数据库] 收到查询: {query[:100]}...")

        # 检测是否为 SQL 语句
        if self._is_sql(query):
            return self._execute_sql(query)

        # 否则进行智能匹配搜索
        return self._smart_search(query, top_n)

    def _is_sql(self, query: str) -> bool:
        """检测 query 是否为 SQL 语句"""
        sql_keywords = ["SELECT", "select", "INSERT", "UPDATE", "DELETE",
                        "CREATE", "ALTER", "DROP", "PRAGMA"]
        return any(query.strip().upper().startswith(kw) for kw in sql_keywords)

    def _execute_sql(self, sql: str) -> str:
        """执行 SQL 并返回结果"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)

            # 如果是 SELECT 类语句
            if sql.strip().upper().startswith("SELECT") or sql.strip().upper().startswith("PRAGMA"):
                rows = cursor.fetchall()
                if not rows:
                    return "查询成功，但没有返回任何数据。"
                return self._format_rows(rows)

            # 如果是写入类语句
            self.conn.commit()
            return f"SQL 执行成功，影响了 {cursor.rowcount} 行。"

        except sqlite3.Error as e:
            log.error(f"[本地数据库] SQL 执行错误: {e}")
            return f"SQL 执行错误: {e}\n表结构如下:\n{self.get_schema_info()}"

    def _smart_search(self, query: str, top_n: int) -> str:
        """
        智能搜索：根据 query 内容匹配最相关的表和列。

        策略：
        1. 获取所有表结构
        2. 优先搜索表名或列名匹配的表
        3. 如果没有匹配，则搜索所有表的数据内容
        4. 返回匹配的数据
        """
        cursor = self.conn.cursor()

        # 获取所有用户表
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        )
        tables = [row['name'] for row in cursor.fetchall()]

        if not tables:
            return "数据库中没有数据表。请先初始化数据。"

        results = []
        keywords = query.lower().split()

        # 找出与关键词匹配的表（表名或列名包含关键词）
        targeted_tables = []
        for table in tables:
            cursor.execute(f"PRAGMA table_info('{table}')")
            columns = cursor.fetchall()
            col_names = [col['name'] for col in columns]

            table_name_match = any(kw in table.lower() for kw in keywords)
            col_name_match = any(
                any(kw in col['name'].lower() for kw in keywords)
                for col in columns
            )

            if table_name_match or col_name_match:
                targeted_tables.append((table, col_names))

        # 如果没有匹配的表，搜索所有表
        if not targeted_tables:
            for table in tables:
                cursor.execute(f"PRAGMA table_info('{table}')")
                columns = cursor.fetchall()
                col_names = [col['name'] for col in columns]
                targeted_tables.append((table, col_names))

        # 搜索目标表中的数据
        for table, col_names in targeted_tables:
            where_clauses = []
            # 只搜索文本类型的列
            for col_name in col_names:
                for kw in keywords:
                    where_clauses.append(f"CAST({col_name} AS TEXT) LIKE '%{kw}%'")

            if where_clauses:
                where_sql = " OR ".join(where_clauses[:10])  # 限制条件数量
                try:
                    cursor.execute(
                        f"SELECT * FROM '{table}' WHERE {where_sql} LIMIT {top_n}"
                    )
                    rows = cursor.fetchall()
                    if rows:
                        results.append(f"\n--- 表 [{table}] ({len(rows)} 条结果) ---")
                        results.append(self._format_rows(rows))
                except sqlite3.Error as e:
                    log.warning(f"搜索表 {table} 时出错: {e}")
                    continue

        if not results:
            return (
                f"未找到匹配 '{query}' 的精确结果。\n\n"
                f"{self.get_schema_info()}\n\n"
                f"提示：请尝试使用 SQL 直接查询，或换个关键词重试。"
            )

        return "\n".join(results)

    def _format_rows(self, rows: list) -> str:
        """格式化查询结果为表格字符串"""
        if not rows:
            return "无数据"

        # 限制返回行数
        rows = rows[:DB_TOP_N]
        columns = rows[0].keys()

        lines = []
        # 表头
        header = " | ".join(columns)
        lines.append(header)
        lines.append("-" * len(header))

        # 数据行
        for row in rows:
            values = [str(row[col]) if row[col] is not None else "NULL" for col in columns]
            lines.append(" | ".join(values))

        return "\n".join(lines)
