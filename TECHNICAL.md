# 企业级智能搜索代理系统 - 技术详解

> 基于 Doubao 大模型 + ReAct 范式 + 多源 RAG 的企业级搜索代理

---

## 目录

1. [系统概览](#1-系统概览)
2. [ReAct 推理范式详解](#2-react-推理范式详解)
3. [RAG 知识库体系](#3-rag-知识库体系)
4. [目录结构](#4-目录结构)
5. [数据流全景](#5-数据流全景)
6. [Web 服务架构](#6-web-服务架构)
7. [配置与日志](#7-配置与日志)

---

## 1. 系统概览

### 1.1 一句话描述

用户提出自然语言问题，系统基于 **ReAct（Reasoning + Acting）** 循环，让 LLM（Doubao）自主决定"先查哪个数据库、用什么关键词、结果是否充分、是否需要换数据源再查"，循环往复直到收集到足够信息后生成最终答案。

### 1.2 整体架构

```
                           用户提问
                              |
              ┌───────────────┼───────────────┐
              ▼                               ▼
       CLI 交互模式                      Web 浏览器
     (python main.py)              (http://内网IP:8080)
              │                               │
              └───────────────┬───────────────┘
                              ▼
              ┌───────────────────────────────┐
              │      SearchAgent              │
              │      (ReAct 推理循环)          │
              │                               │
              │  ┌──────┐   ┌──────┐   ┌───┐ │
              │  │ 思考  │──▶│ 决策  │──▶│执行│ │
              │  │      │◀──│      │◀──│   │ │
              │  └──────┘   └──────┘   └───┘ │
              │       ↑ 信息不足则继续  │      │
              │       └────────────────┘      │
              │                │               │
              │           信息充足             │
              │                ▼               │
              │         生成最终答案            │
              └───────────────┬───────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
   ┌──────────┐        ┌──────────┐        ┌──────────┐
   │ SQLite   │        │ ChromaDB │        │ Whoosh   │
   │ 结构化数据│        │ 语义搜索  │        │ 关键词搜索│
   └──────────┘        └──────────┘        └──────────┘
         │                    │                    │
         ▼                    ▼                    ▼
   ┌──────────┐        ┌──────────────────────────────┐
   │ CodeRepo │        │  EnterpriseSDK               │
   │ 代码搜索  │        │  HR / CRM / ERP / 知识库     │
   └──────────┘        └──────────────────────────────┘
```

### 1.3 核心概念

| 概念 | 说明 |
|------|------|
| **SearchAgent** | 智能搜索代理，实现 ReAct 循环逻辑 |
| **DoubaoLLM** | 豆包大模型客户端，调用火山引擎 Ark API |
| **ToolRegistry** | 工具注册表，管理 5 个搜索工具的定义和执行 |
| **Tool Definition** | 每个搜索后端以 OpenAI Function Calling 格式暴露给 LLM |
| **SSE** | Server-Sent Events，Web 模式下的实时流式传输协议 |

---

## 2. ReAct 推理范式详解

### 2.1 什么是 ReAct

ReAct = **Reasoning（推理）+ Acting（行动）**，是一种让 LLM 在"思考"和"行动"之间交替进行的范式。与传统的一问一答不同，ReAct 允许模型在回答前进行多轮信息收集。

### 2.2 循环状态机

```
                  ┌─────────────────┐
                  │   接收用户问题    │
                  └────────┬────────┘
                           ▼
              ┌────────────────────────┐
              │   LLM 分析问题意图       │  ← Reasoning
              │   (理解要查什么)         │
              └────────────┬───────────┘
                           ▼
              ┌────────────────────────┐
              │   LLM 选择搜索工具       │  ← Decision
              │   (5 选 1，选最佳匹配)    │
              └────────────┬───────────┘
                           ▼
              ┌────────────────────────┐
              │   执行工具调用           │  ← Acting
              │   (搜索底层数据库)        │
              └────────────┬───────────┘
                           ▼
              ┌────────────────────────┐
              │   LLM 审阅搜索结果       │  ← Evaluation
              │   信息是否充足？          │
              └────────────┬───────────┘
                    │              │
               信息不足          信息充足
                    │              │
                    ▼              ▼
           返回"选择工具"    ┌──────────────┐
           换数据源/换关键词  │ 生成最终答案   │
                            └──────────────┘
```

### 2.3 代码实现（agent/core.py → SearchAgent.run()）

```python
# 伪代码还原核心循环
def run(self, user_query):
    self.messages = [
        {"role": "system", "content": SYSTEM_PROMPT},  # 告诉 LLM 它是搜索代理
        {"role": "user",   "content": user_query}
    ]

    for iteration in range(MAX_SEARCH_ITERATIONS):  # 默认最多 10 轮
        # Step 1: 调 LLM，给它工具列表让它决策
        response = self.llm.chat(
            messages=self.messages,
            tools=self.tools.get_definitions(),  # 5 个工具的 OpenAI 格式定义
            tool_choice="auto"                   # LLM 自主决定是否调工具
        )

        if response["tool_calls"]:
            # LLM 决定调工具 → 执行 + 把结果追加到对话历史
            self._handle_tool_calls(response)
            # → 下一轮循环，LLM 会看到工具结果并重新决策
        else:
            # LLM 认为信息够了 → 直接返回最终答案
            return response["content"]
```

### 2.4 System Prompt 的作用

`agent/core.py` 中的 `SYSTEM_PROMPT`（约 100 行）是整个 ReAct 范式的"操作手册"，它明确告诉 LLM：

- 你是一个企业搜索代理，不是普通聊天机器人
- 你有 5 个搜索工具，每个工具的适用场景是什么
- 每次只调用一个工具，思考 → 选择 → 执行 → 评估 → 再决策
- 什么时候该停止搜索、什么时候该换工具
- 答案要引用数据来源

### 2.5 关键设计决策

| 决策 | 原因 |
|------|------|
| 每次只调一个工具 | 降低 LLM 决策复杂度，避免无效的并行搜索 |
| 搜索结果截断到 4000 字符 | 防止超出 LLM token 限制 |
| 最多 10 轮搜索 | 防止死循环，强制在 10 轮内给出答案 |
| 低温度（0.3） | 保证推理稳定性，降低幻觉 |

---

## 3. RAG 知识库体系

系统有 5 个独立的知识库（搜索后端），覆盖不同类型的数据检索需求。

### 3.1 SQLite 关系数据库

**文件**: `backends/database.py`  
**技术**: SQLite3 + 自然语言映射  
**数据**: 5 张表 / 约 40 条记录

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  employees  │  │ departments │  │  projects   │  │    sales    │  │  inventory  │
├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤
│ id          │  │ id          │  │ id          │  │ id          │  │ id          │
│ name        │  │ name        │  │ name        │  │ customer    │  │ name        │
│ department  │  │ manager_id  │  │ department  │  │ amount      │  │ category    │
│ position    │  │ emp_count   │  │ owner       │  │ product     │  │ quantity    │
│ email       │  │ budget      │  │ status      │  │ sales_rep   │  │ unit_price  │
│ phone       │  │             │  │ start_date  │  │ date        │  │ warehouse   │
│ hire_date   │  │             │  │ end_date    │  │ region      │  │             │
│ salary      │  │             │  │ budget      │  │             │  │             │
│ manager_id  │  │             │  │ description │  │             │  │             │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
    12 行            5 行            5 行            7 行            5 行
```

#### 搜索策略

```
query 进入
    │
    ├── 以 SELECT/INSERT/UPDATE 开头？ ──→ 直接执行 SQL
    │
    └── 自然语言？ ──→ 智能匹配流程：
            │
            ├── 1. 提取关键词
            ├── 2. 匹配表名和列名（如 query 含"员工" → 查 employees 表）
            ├── 3. 在匹配的表的文本列中做 LIKE 搜索
            ├── 4. 找不到？返回完整表结构给 LLM 参考
            └── 5. 格式化输出（表头 + 分隔线 + 数据行）
```

### 3.2 ChromaDB 向量数据库

**文件**: `backends/vector_db.py`  
**技术**: ChromaDB（持久化）+ 嵌入模型（三级降级策略）

#### 嵌入模型优先级

```
优先级 1: Doubao 文本嵌入 API (doubao-embedding-text-240715)
    │      需要 API Key，网络友好，质量最高
    │
    ▼ 失败
优先级 2: 本地 TF-IDF (scikit-learn + jieba 分词)
    │      纯本地，无需联网，无需 GPU
    │
    ▼ 失败
优先级 3: 本地 sentence-transformers
    (paraphrase-multilingual-MiniLM-L12-v2)
            需要能访问 HuggingFace 下载模型
```

#### 搜索流程

```
用户 query: "如何提升系统安全性？"
    │
    ├── 1. jieba 分词 → ["如何", "提升", "系统", "安全性"]
    │
    ├── 2. 嵌入模型 → [0.023, -0.451, 0.891, ...] (向量)
    │
    ├── 3. ChromaDB 余弦相似度搜索 → Top-K 最相似文档
    │
    └── 4. 返回结果：相似度分数 + 文档标题 + 来源 + 内容预览
```

#### 初始数据

7 篇企业文档，在 `seed_data.py` 中定义：
- 技术部年度规划（容器化、数据中台、AI 工具）
- 网络安全事件响应预案
- 大数据平台技术选型报告
- 员工绩效考核管理办法
- 微服务架构设计规范
- Q1 销售业绩报告
- 公司数字化转型战略白皮书

### 3.3 Whoosh 关键词搜索引擎

**文件**: `backends/keyword_search.py`  
**技术**: Whoosh（倒排索引）+ jieba（中文分词）

#### 索引结构

```python
Schema(
    doc_id   = ID(stored=True, unique=True),    # 唯一标识
    title    = TEXT(stored=True),                # 标题（可搜索）
    content  = TEXT(stored=True),                # 正文（可搜索）
    source   = ID(stored=True),                  # 来源部门
    tags     = KEYWORD(stored=True, commas=True) # 标签（逗号分隔）
)
```

#### 为什么用 jieba + Whoosh 而不是直接用数据库 LIKE？

- LIKE 做不了中文分词，搜"系统安全"找不到"信息安全管理"
- Whoosh 倒排索引比 LIKE 快很多
- jieba 能把"系统安全"切成"系统"+"安全"，分别匹配索引

#### 搜索流程

```
query: "微服务架构"
    │
    ├── 1. jieba.cut("微服务架构") → ["微服务", "架构"]
    │
    ├── 2. 用空格连接 → "微服务 架构"
    │
    ├── 3. Whoosh MultifieldParser 解析（在 title + content + tags 中搜）
    │
    ├── 4. 倒排索引查找 → 得分排序
    │
    └── 5. 无结果？用原始 query 重试（处理英文关键词）
```

### 3.4 代码仓库搜索

**文件**: `backends/code_repo.py`  
**技术**: 文件系统遍历 + grep + 正则匹配

#### 支持的查询格式

| 格式 | 示例 | 说明 |
|------|------|------|
| `file:xxx` | `file:gateway` | 按文件名搜索 |
| `def xxx` / `func:xxx` | `def verify_token` | 搜索函数定义 |
| `class xxx` | `class SearchAgent` | 搜索类定义 |
| `list` | `list` | 列出所有文件 |
| 自由文本 | `JWT token` | 按内容 grep 搜索 |

#### 支持的代码文件类型

30+ 种扩展名：`.py`, `.js`, `.ts`, `.java`, `.go`, `.yaml`, `.json`, `.sql` 等

#### 搜索策略

```
grep 搜索:
    ├── 1. 先用 AND 逻辑（所有关键词都必须命中）
    ├── 2. 没结果？改用 OR 逻辑（任一关键词命中即可）
    └── 3. 返回：文件路径:行号 + 匹配行内容

定义搜索:
    └── 按语言分别匹配：
        Python:   ^\s*(def|class)\s+...
        JS/TS:    function\s+... | ...= function | class
        Java:     public/private... + methodName(
        Go:       func\s+...(
        C/C++:    type funcName(...) {
```

### 3.5 企业系统 SDK

**文件**: `backends/enterprise_sdk.py`  
**数据**: 纯内存模拟，约 50 条虚构企业数据

```
EnterpriseSDK (统一入口)
    │
    ├── HRSystem      # 10 个员工 + 自动识别部门/人名
    │   ├── query_employee("张伟")
    │   ├── query_department("技术部")
    │   └── get_all_departments()
    │
    ├── CRMSystem      # 10 个客户 + 等级分类
    │   ├── query_customer("阿里巴巴")
    │   ├── list_by_level("VIP")
    │   └── get_pipeline()
    │
    ├── ERPSystem      # 8 种物料 + 3 个仓库
    │   ├── query_inventory("服务器")
    │   ├── list_by_warehouse("北京仓")
    │   └── get_inventory_summary()
    │
    ├── KnowledgeManagement  # 5 篇制度文档
    │   ├── search("报销")
    │   └── list_categories()
    │
    └── ProjectQuery   # 5 个项目
        └── 按名称/负责人/状态/部门过滤
```

#### 智能路由

`EnterpriseSDK.query()` 通过关键词自动路由到对应子系统：

```
query 含 "员工/部门/人事/职位/总监" → HRSystem
query 含 "客户/销售/营收/VIP"       → CRMSystem
query 含 "库存/物料/仓库/设备"       → ERPSystem
query 含 "制度/流程/规范/报销/审批"   → KnowledgeManagement
query 含 "项目"                      → ProjectQuery
```

---

## 4. 目录结构

```
agentic_search/
│
├── agent/                           # 【智能代理层】ReAct 核心
│   ├── __init__.py                  # 包初始化
│   ├── core.py                      # SearchAgent 类，ReAct 循环主逻辑
│   ├── llm.py                       # DoubaoLLM 类，封装火山引擎 Ark API
│   └── tools.py                     # ToolRegistry 类，管理 5 个搜索工具
│
├── backends/                        # 【搜索后端层】5 个独立知识库
│   ├── __init__.py
│   ├── database.py                  # SQLite 结构化数据搜索
│   ├── vector_db.py                 # ChromaDB 语义向量搜索
│   ├── keyword_search.py            # Whoosh 关键词全文检索
│   ├── code_repo.py                 # 代码仓库 grep 搜索
│   └── enterprise_sdk.py            # 企业系统模拟 (HR/CRM/ERP/KM)
│
├── web_ui/                          # 【Web 前端】聊天界面
│   └── index.html                   # 暖色调单页应用 (SSE + Markdown)
│
├── web_server.py                    # 【Web 服务】Flask + SSE 流式响应
├── main.py                          # 【CLI 入口】支持交互/查询/Web/状态
├── config.py                        # 【配置】环境变量统一管理
├── logger_setup.py                  # 【日志】彩色终端 + 文件轮转
├── seed_data.py                     # 【数据初始化】一键填充所有后端
│
├── data/                            # 【运行时数据】自动生成
│   ├── local.db                     #   SQLite 数据库文件
│   ├── documents/                   #   7 篇示例文档 (.txt)
│   ├── code_samples/                #   3 个示例代码文件
│   ├── vector_db/                   #   ChromaDB 持久化目录
│   └── keyword_index/               #   Whoosh 索引文件
│
├── logs/                            # 【日志文件】自动轮转
│   └── agent.log                    #   结构化日志 (10MB/文件, 保留5个)
│
├── requirements.txt                 # 【依赖】Python 包清单
└── .env.example                     # 【环境变量模板】
```

### 逐文件说明

| 文件 | 职责 | 关键类/函数 |
|------|------|------------|
| `agent/core.py` | ReAct 循环引擎 | `SearchAgent.run()` — 主循环;<br>`SYSTEM_PROMPT` — LLM 行为规范 |
| `agent/llm.py` | LLM 通信层 | `DoubaoLLM.chat()` — 对话+工具调用;<br>`DoubaoLLM.force_final_answer()` — 强制生成答案 |
| `agent/tools.py` | 工具注册与调度 | `ToolRegistry.execute()` — 统一调用入口;<br>5 个 `_register_tool()` — OpenAI Function Calling 格式定义 |
| `backends/database.py` | SQLite 搜索 | `LocalDatabase.search()` — SQL/自然语言双模式;<br>`_smart_search()` — 关键词→表列匹配 |
| `backends/vector_db.py` | 语义向量搜索 | `VectorDatabase.search()` — 余弦相似度检索;<br>三级嵌入模型降级策略 |
| `backends/keyword_search.py` | 全文关键词搜索 | `KeywordSearchEngine.search()` — 中文分词+倒排索引;<br>`preprocess_chinese()` — jieba 预处理 |
| `backends/code_repo.py` | 代码仓库搜索 | `CodeRepository.search()` — 文件/grep/定义/list 四模式 |
| `backends/enterprise_sdk.py` | 企业系统模拟 | `EnterpriseSDK.query()` — 关键词智能路由;<br>HR/CRM/ERP/KM 四个子系统 |
| `web_server.py` | Flask Web 服务 | SSE 流式响应;<br>后台线程执行搜索 + 事件队列 |
| `web_ui/index.html` | 聊天前端 | SSE 客户端 + marked.js Markdown 渲染;<br>搜索步骤分组 + 可折叠工具消息 |
| `main.py` | CLI 入口 | 5 种子命令: seed / web / status / query / interactive |
| `config.py` | 配置管理 | 所有环境变量读取 + 路径初始化 |
| `logger_setup.py` | 日志系统 | 彩色终端 + RotatingFileHandler 文件轮转 |
| `seed_data.py` | 数据初始化 | 5 个 `seed_xxx()` 函数，一键填充所有后端 |

---

## 5. 数据流全景

以用户提问"技术部有哪些进行中的项目？"为例，完整追踪数据流向：

### 5.1 第 1 轮

```
用户: "技术部有哪些进行中的项目？"
    │
    ▼
SearchAgent.run()
    │
    ├── messages = [system_prompt, user_query]
    │
    ▼
DoubaoLLM.chat(messages, tools=5个工具定义)
    │
    │  LLM 阅读 SYSTEM_PROMPT 中的工具描述：
    │  "search_local_database: 适合查询结构化数据，如员工信息、项目记录..."
    │
    │  LLM 推理: "项目信息很可能在数据库的 projects 表中，
    │             我构造一条 SQL 来查询"
    │
    ▼
LLM 返回: tool_calls = [{
    name: "search_local_database",
    arguments: {"query": "SELECT * FROM projects WHERE department='技术部' AND status='进行中'"}
}]
    │
    ▼
ToolRegistry.execute("search_local_database", ...)
    │
    ▼
LocalDatabase.search("SELECT * FROM projects WHERE department='技术部' AND status='进行中'")
    │
    ├── _is_sql() → True → _execute_sql()
    │
    ▼
返回: "id | name | department | owner | status | ...\n
       P001 | 智能客服系统升级 | 技术部 | 张伟 | 进行中 | ...\n
       P002 | ERP系统国产化迁移 | 技术部 | 李娜 | 进行中 | ...\n
       P004 | 网络安全等级保护2.0 | 技术部 | 孙鹏 | 进行中 | ..."
    │
    ▼
追加到 messages:
    assistant: {tool_calls: [...]}
    tool: {content: "数据库返回了3个项目..."}
    │
    ▼
回到循环开头，第 2 轮...
```

### 5.2 第 2 轮

```
DoubaoLLM.chat(messages)  ← messages 中现在包含工具调用结果
    │
    │  LLM 看到数据库返回了 3 个项目
    │  LLM 推理: "数据比较完整，但我还想确认企业系统里
    │             是否有更多细节（预算使用情况等）"
    │
    ▼
LLM 返回: tool_calls = [{
    name: "query_enterprise_system",
    arguments: {"query": "技术部进行中的项目"}
}]
    │
    ▼
EnterpriseSDK.query("技术部进行中的项目")
    │
    ├── 关键词匹配: "项目" in query → _query_projects()
    │   → 按 department="技术部" 过滤 → 返回 3 个项目
    │
    ▼
追加到 messages → 第 3 轮...
```

### 5.3 第 3 轮

```
DoubaoLLM.chat(messages)  ← 现在有 SQLite 和 EnterpriseSDK 两个来源的结果
    │
    │  LLM 推理: "两个数据源互相印证，信息已经充足。
    │             项目名称、负责人、周期、预算都已获取。"
    │
    │  LLM 决定: 不调工具了，直接给答案
    │
    ▼
LLM 返回: content = "技术部目前有3个进行中的项目：
                    1. 智能客服系统升级 (P001) — 张伟 — 500万
                    2. ERP系统国产化迁移 (P002) — 李娜 — 800万
                    3. 网络安全等级保护2.0 (P004) — 孙鹏 — 200万
                    ..."
    │
    ▼
SearchAgent 检测到无 tool_calls → 返回最终答案
```

---

## 6. Web 服务架构

### 6.1 通信协议

```
浏览器 ←──── SSE (Server-Sent Events) ────→ Flask (:8080)
               单向流（服务端 → 客户端）

事件类型:
  status     → 搜索开始
  thinking   → LLM 推理文本
  tool_call  → 调用了哪个工具
  tool_result → 工具返回了什么
  iteration  → 当前第几轮
  answer     → 最终答案
  done       → 搜索完成
  error      → 出错了
```

### 6.2 线程模型

```
Flask 主线程: 接收 HTTP 请求
    │
    ├── GET  /          → 返回 index.html
    ├── GET  /api/health → 返回 {"status": "ok"}
    │
    └── POST /api/chat  → 创建后台线程 + 返回 SSE 流
                              │
                     ┌────────┴────────┐
                     │  daemon thread  │
                     │  SearchAgent    │
                     │  .run(query)    │
                     │       │         │
                     │  实时写入 queue  │
                     └────────┬────────┘
                              │
                     ┌────────┴────────┐
                     │  SSE generate() │
                     │  读 queue       │
                     │  yield 事件      │
                     └─────────────────┘
```

### 6.3 安全性

- API Key 仅存在于服务端 `.env` 文件和进程内存中
- 客户端收到的 SSE 流只包含搜索内容，不含任何密钥
- `.env` 已加入 `.gitignore`，不会提交到版本控制

---

## 7. 配置与日志

### 7.1 配置项（.env）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DOUBAO_API_KEY` | - | 火山引擎 API Key（必填） |
| `DOUBAO_MODEL` | `doubao-pro-32k` | LLM 模型 |
| `DOUBAO_BASE_URL` | `https://ark.cn-beijing.volces.com/api/v3` | API 地址 |
| `MAX_SEARCH_ITERATIONS` | `10` | ReAct 最大循环轮次 |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | 本地嵌入模型 |
| `TOP_K_VECTOR` | `5` | 向量搜索返回数 |
| `LOG_LEVEL` | `INFO` | 日志级别 |

### 7.2 日志系统

```
终端输出 (彩色):
  14:30:22 | INFO     | [搜索代理] 开始处理用户问题: ...
  14:30:22 | DEBUG    | [Doubao LLM] 发送请求，消息数=2
  14:30:25 | INFO     | [Doubao LLM] 决定调用工具: search_local_database
  14:30:25 | INFO     | [工具执行] ▶ search_local_database | query='SELECT...'
  14:30:25 | INFO     | [工具执行] ✅ 完成 | 结果=850字符 | 耗时=0.12s

文件日志 (logs/agent.log):
  2026-07-03 14:30:22 | INFO     | AgenticSearch | run:158 | 开始处理用户问题: ...
  自动轮转：10MB/文件，保留 5 个历史文件
```

### 7.3 日志记录内容

- 每次 LLM API 调用的耗时和 token 用量
- 每次工具调用的查询内容、结果长度、执行耗时
- 每一轮推理的决策过程
- 完整的对话消息历史（DEBUG 级别）
- 异常和错误的完整堆栈
