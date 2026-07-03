# 🔍 企业级智能搜索代理系统

**Agentic Search System with Doubao Reasoning**

一个基于 **Doubao（豆包）大模型** 的多源智能搜索代理。通过 **ReAct（Reasoning + Acting）** 模式，让 LLM 自主决策搜索策略：先搜什么、怎么搜、下一步搜什么，循环往复直到获得足够信息回答用户问题。

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        用户提问                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   🔍 SearchAgent (ReAct循环)                 │
│                                                             │
│   ┌──────────┐    ┌──────────┐    ┌──────────────────┐     │
│   │ 思考分析  │───▶│ 选择工具  │───▶│  执行搜索         │     │
│   │ (Doubao) │◀───│ (Doubao) │◀───│ (Tool Execution)  │     │
│   └──────────┘    └──────────┘    └──────────────────┘     │
│         │                                            │      │
│         │          信息不足，继续搜索                   │      │
│         └────────────────────────────────────────────┘      │
│                         │                                   │
│                    信息充足                                  │
│                         ▼                                   │
│              生成最终答案 (Doubao)                           │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     📚 五大搜索后端                          │
├──────────────┬──────────────┬──────────────┬────────────────┤
│  SQLite DB   │  ChromaDB    │  Whoosh      │  Code Repo     │
│  结构化数据   │  语义搜索     │  关键词搜索   │  代码搜索       │
├──────────────┴──────────────┴──────────────┴────────────────┤
│              企业系统SDK (HR/CRM/ERP/知识库)                  │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 ReAct 推理循环

每个搜索请求都经历一个完整的 **推理-行动-观察** 循环：

1. **分析问题** → Doubao 理解用户意图，识别信息需求
2. **制定策略** → 决定优先搜索哪个数据源（首次决策）
3. **执行搜索** → 调用选定的搜索后端
4. **评估结果** → Doubao 审阅搜索结果，判断是否充足
5. **循环决策** → 如果不足，选择下一个最合适的工具继续搜索
6. **生成答案** → 综合所有搜索结果给出最终回答

## 🚀 快速开始

### 1. 安装依赖

```bash
cd agentic_search
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的 Doubao API Key
# DOUBAO_API_KEY=你的API密钥
```

> 获取 API Key: [火山引擎 Ark 控制台](https://console.volcengine.com/ark)

### 3. 初始化示例数据

```bash
python main.py --seed
```

这会初始化所有数据源：
- SQLite 数据库（员工、部门、项目、销售、库存表）
- 向量数据库（7篇企业文档的嵌入向量）
- 关键词索引（中文全文检索索引）
- 代码示例文件（Python API网关、K8s部署配置等）

### 4. 开始搜索

```bash
# 交互模式
python main.py

# 单次查询
python main.py -q "技术部有哪些员工？"

# 查看系统状态
python main.py --status
```

## 📖 使用示例

### 交互模式

```
🔍 请输入你的问题: 技术部有哪些进行中的项目？

⏳ 正在搜索: 技术部有哪些进行中的项目？

[Doubao LLM] 💭 思考: 用户要查询技术部进行中的项目，这是结构化数据查询。
我优先使用本地数据库搜索...

[Doubao LLM] 🔧 决定调用工具: search_local_database
[工具执行] ▶ search_local_database | query='SELECT * FROM projects...'

[Doubao LLM] 💭 思考: 数据库返回了3个进行中的项目，信息比较完整。
我还想通过企业系统确认一下项目预算执行情况...

[Doubao LLM] 🔧 决定调用工具: query_enterprise_system
[工具执行] ▶ query_enterprise_system | query='技术部进行中的项目'

[Doubao LLM] 🎯 信息充足，生成最终答案

📝 最终答案:
技术部目前有3个进行中的项目：

1. **智能客服系统升级** (P001)
   - 负责人: 张伟（技术总监）
   - 周期: 2026-01-10 ~ 2026-08-30
   - 预算: ¥5,000,000
   ...

📊 工具调用历史（共2次）:
  1. search_local_database | 结果=850字符 | 耗时=0.12s
  2. query_enterprise_system | 结果=420字符 | 耗时=0.05s
```

### Python API

```python
from agentic_search import SearchAgent

# 创建代理
agent = SearchAgent()

# 搜索
answer = agent.run("公司Q1的销售业绩如何？")
print(answer)

# 查看调用历史
print(agent.tools.get_call_summary())
```

## 🗂️ 项目结构

```
agentic_search/
├── agent/                      # 智能代理层
│   ├── __init__.py
│   ├── core.py                 # ReAct 循环核心
│   ├── llm.py                  # Doubao LLM 集成
│   └── tools.py                # 工具注册表
├── backends/                   # 搜索后端
│   ├── __init__.py
│   ├── database.py             # SQLite 关系数据库
│   ├── vector_db.py            # ChromaDB 向量数据库
│   ├── keyword_search.py       # Whoosh 关键词搜索
│   ├── code_repo.py            # 代码仓库搜索
│   └── enterprise_sdk.py       # 企业系统SDK模拟
├── web_ui/                     # Web 聊天界面
│   └── index.html              # 现代化聊天网页
├── web_server.py               # Flask Web 服务
├── data/                       # 数据目录（自动生成）
├── logs/                       # 日志目录
├── config.py                   # 系统配置
├── logger_setup.py             # 日志系统
├── seed_data.py                # 数据初始化
├── main.py                     # CLI入口（含 --web 启动Web服务）
├── requirements.txt            # 依赖清单
└── .env.example                # 环境变量模板
```

## 🔧 五种搜索后端

| 后端 | 技术栈 | 适用场景 | 搜索方式 |
|------|--------|---------|---------|
| **本地数据库** | SQLite | 结构化数据（员工/项目/销售） | SQL查询 + 智能表匹配 |
| **向量数据库** | ChromaDB + sentence-transformers | 文档语义搜索 | 向量相似度（Cosine） |
| **关键词搜索** | Whoosh + jieba分词 | 精确术语查找 | 全文倒排索引 |
| **代码仓库** | 文件系统 + grep | 代码/配置文件搜索 | 文件名/内容/正则匹配 |
| **企业SDK** | Python模拟 | HR/CRM/ERP/知识库 | 智能路由到子系统 |

## 🧠 Doubao 决策示例

Doubao 模型会根据问题类型自动选择合适的搜索策略：

| 用户问题 | Doubao 的推理 | 首选工具 |
|---------|-------------|---------|
| "张伟是哪个部门的？" | 精确实体查询 → 数据库或HR系统 | `search_local_database` |
| "如何提升系统安全性？" | 概念性问题 → 语义搜索 | `search_vector_database` |
| "微服务架构规范" | 特定术语 → 全文检索 | `search_keywords` |
| "API网关怎么实现认证？" | 代码实现问题 → 代码仓库 | `search_code_repository` |
| "公司有哪些VIP客户？" | 企业内部数据 → 企业系统 | `query_enterprise_system` |

## 📊 日志系统

所有操作都被记录到结构化日志中：

- **终端输出**: 彩色分级日志（DEBUG/INFO/WARNING/ERROR）
- **文件日志**: `logs/agent.log`，自动轮转（10MB/文件，保留5个历史）
- **记录内容**: 工具调用、LLM推理过程、搜索结果、耗时统计

## ⚙️ 配置项

所有配置通过 `.env` 文件或环境变量设置：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `DOUBAO_API_KEY` | - | 豆包API密钥（必填） |
| `DOUBAO_MODEL` | `doubao-pro-32k` | 使用的模型 |
| `MAX_SEARCH_ITERATIONS` | `10` | 最大搜索轮次 |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | 向量嵌入模型 |
| `TOP_K_VECTOR` | `5` | 向量搜索返回数 |
| `LOG_LEVEL` | `INFO` | 日志级别 |

