# 企业级智能搜索代理系统

**Agentic Search System with Doubao Reasoning**

基于 **Doubao（豆包）大模型** 的多源智能搜索代理。通过 **ReAct（Reasoning + Acting）** 模式，让 LLM 自主决策搜索策略：先搜什么、怎么搜、下一步搜什么，循环往复直到获得足够信息回答用户问题。

支持 **CLI 交互** 和 **Web 服务** 两种使用方式。Web 模式可部署到内网，多人通过浏览器同时使用，API Key 仅存服务端、不会泄露。

---

## 系统架构

```
                        用户提问
                           |
          ┌────────────────┼────────────────┐
          ▼                                 ▼
    CLI 交互模式                        Web 浏览器
   (python main.py)              (http://内网IP:8080)
          │                                 │
          └────────────────┬────────────────┘
                           ▼
              SearchAgent (ReAct 循环)
                           |
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         思考分析  →  选择工具  →  执行搜索
              ▲                         │
              └──── 结果反馈 ←──────────┘
                           |
                    信息充足则生成答案
                           |
          ┌────────────────┼────────────────┐
          ▼            ▼            ▼        ▼         ▼
      SQLite DB    ChromaDB     Whoosh    CodeRepo  企业SDK
      结构化数据    语义搜索     关键词搜索  代码搜索   HR/CRM/ERP
```

## ReAct 推理循环

每次搜索经历完整的 **推理-行动-观察** 循环：

1. **分析问题** → Doubao 理解用户意图
2. **制定策略** → 决定优先搜索哪个数据源
3. **执行搜索** → 调用选定的搜索后端
4. **评估结果** → 审阅结果，判断是否充足
5. **循环决策** → 不足则换工具继续搜
6. **生成答案** → 综合所有信息给出最终回答

## 快速开始

### 1. 安装依赖

```bash
cd agentic_search
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入 Doubao API Key
```

> 获取 Key: [火山引擎 Ark 控制台](https://console.volcengine.com/ark)

### 3. 初始化数据

```bash
python main.py --seed
```

### 4. 启动

```bash
# Web 服务（推荐，局域网可访问）
python main.py --web

# 自定义端口
python main.py --web --port 9090

# CLI 交互模式
python main.py

# 单次查询
python main.py -q "技术部有哪些员工？"

# 查看系统状态
python main.py --status
```

## Web 服务（内网部署）

启动后局域网内其他设备通过浏览器访问，无需安装任何软件：

```
http://<本机IP>:8080
```

**安全说明：** API Key 仅存储在服务端 `.env` 文件中，所有 LLM 调用在服务端完成。浏览器通过 SSE（Server-Sent Events）流式接收搜索结果，全程不接触 API Key。

Web 界面特性：
- 暖色调现代化设计
- Markdown 渲染（标题、表格、代码块、列表）
- 实时流式展示思考过程与工具调用
- 工具消息可折叠/展开
- 消息一键复制
- 搜索步骤分组展示

## 使用示例

### Web 模式

浏览器打开后输入问题，系统实时展示：
- LLM 的推理思考过程
- 每一步调用了什么工具、查到了什么
- 最终的综合答案（Markdown 渲染）

### CLI 交互模式

```
请输入你的问题: 技术部有哪些进行中的项目？

[Doubao LLM] 思考: 这是结构化数据查询，优先使用数据库搜索...
[工具执行] search_local_database | query='SELECT * FROM projects...'
[Doubao LLM] 评估: 数据库返回了3个项目，还需确认企业系统数据...
[工具执行] query_enterprise_system | query='技术部进行中的项目'
[Doubao LLM] 信息充足，生成最终答案

最终答案:
技术部目前有3个进行中的项目：
1. 智能客服系统升级 (P001) - 负责人: 张伟 - 预算: 500万
2. 数据中台建设 (P003) - 负责人: 李明 - 预算: 300万
...

工具调用统计: 共2次 | 总耗时: 1.8s
```

### Python API

```python
from agent.core import SearchAgent

agent = SearchAgent()
answer = agent.run("公司Q1的销售业绩如何？")
print(answer)
print(agent.tools.get_call_summary())
```

## 项目结构

```
agentic_search/
├── agent/                      # 智能代理层
│   ├── core.py                 # ReAct 循环核心
│   ├── llm.py                  # Doubao LLM 集成
│   └── tools.py                # 工具注册表
├── backends/                   # 搜索后端
│   ├── database.py             # SQLite 关系数据库
│   ├── vector_db.py            # ChromaDB 向量数据库
│   ├── keyword_search.py       # Whoosh 关键词搜索
│   ├── code_repo.py            # 代码仓库搜索
│   └── enterprise_sdk.py       # 企业系统 SDK 模拟
├── web_ui/                     # Web 聊天界面
│   └── index.html              # 暖色调现代化聊天网页
├── web_server.py               # Flask Web 服务（SSE 流式响应）
├── data/                       # 数据目录（运行时生成）
├── logs/                       # 日志目录
├── config.py                   # 系统配置
├── logger_setup.py             # 日志系统
├── seed_data.py                # 数据初始化
├── main.py                     # 入口（支持 CLI / Web / 查询 / 状态）
├── requirements.txt            # 依赖清单
└── .env.example                # 环境变量模板
```

## 五种搜索后端

| 后端 | 技术栈 | 适用场景 |
|------|--------|---------|
| 本地数据库 | SQLite | 结构化数据（员工/项目/销售） |
| 向量数据库 | ChromaDB + sentence-transformers | 文档语义搜索 |
| 关键词搜索 | Whoosh + jieba 分词 | 精确术语查找 |
| 代码仓库 | 文件系统 + grep | 代码和配置文件搜索 |
| 企业 SDK | Python 模拟 | HR / CRM / ERP / 知识库 |

## 配置项

所有配置通过 `.env` 文件设置：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `DOUBAO_API_KEY` | - | 豆包 API 密钥（必填） |
| `DOUBAO_MODEL` | `doubao-pro-32k` | 使用的模型 |
| `MAX_SEARCH_ITERATIONS` | `10` | 最大搜索轮次 |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | 向量嵌入模型 |
| `TOP_K_VECTOR` | `5` | 向量搜索返回数 |
| `LOG_LEVEL` | `INFO` | 日志级别 |

## 日志

所有操作记录到结构化日志中：

- 终端输出：彩色分级（DEBUG/INFO/WARNING/ERROR）
- 文件：`logs/agent.log`，自动轮转（10MB/文件，保留 5 个）
- 内容：工具调用、LLM 推理过程、搜索结果、耗时统计
