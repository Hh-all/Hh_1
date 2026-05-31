"""
============================================================
数据初始化脚本 - 为所有搜索后端填充示例数据
Data Seeder - Populates all backends with sample data
============================================================

运行此脚本以初始化：
1. SQLite 数据库（表 + 数据）
2. 向量数据库（文档嵌入）
3. 关键词索引（全文索引）
4. 代码示例文件
5. 企业系统数据（已在 enterprise_sdk.py 中定义）

使用方法:
    python seed_data.py
"""
import sqlite3
import os
import sys
from pathlib import Path

# 允许直接运行此脚本
sys.path.insert(0, str(Path(__file__).parent))

from config import DB_PATH, DATA_DIR, DOCUMENTS_DIR, CODE_SAMPLES_DIR
from logger_setup import log


# ============================================================
# 1. SQLite 数据库初始化
# ============================================================

def seed_database():
    """创建数据库表并插入示例数据"""
    log.info("=" * 50)
    log.info("📦 初始化 SQLite 数据库...")
    log.info("=" * 50)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # ---- 创建表 ----
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT,
            position TEXT,
            email TEXT,
            phone TEXT,
            hire_date TEXT,
            salary REAL,
            manager_id TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            manager_id TEXT,
            employee_count INTEGER,
            budget REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT,
            owner TEXT,
            status TEXT,
            start_date TEXT,
            end_date TEXT,
            budget REAL,
            description TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            amount REAL,
            product TEXT,
            sales_rep TEXT,
            date TEXT,
            region TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id TEXT PRIMARY KEY,
            name TEXT,
            category TEXT,
            quantity INTEGER,
            unit TEXT,
            unit_price REAL,
            warehouse TEXT
        )
    """)

    # ---- 清空旧数据 ----
    for table in ["employees", "departments", "projects", "sales", "inventory"]:
        cursor.execute(f"DELETE FROM {table}")

    # ---- 插入员工数据 ----
    employees_data = [
        ("E001", "张伟", "技术部", "技术总监", "zhangwei@company.com", "13800001001", "2020-01-15", 450000, None),
        ("E002", "李娜", "技术部", "高级工程师", "lina@company.com", "13800001002", "2020-03-20", 350000, "E001"),
        ("E003", "王磊", "技术部", "前端工程师", "wanglei@company.com", "13800001003", "2021-06-01", 250000, "E002"),
        ("E004", "赵敏", "产品部", "产品总监", "zhaomin@company.com", "13800001004", "2020-02-10", 420000, None),
        ("E005", "陈刚", "产品部", "产品经理", "chengang@company.com", "13800001005", "2021-01-05", 280000, "E004"),
        ("E006", "刘洋", "销售部", "销售总监", "liuyang@company.com", "13800001006", "2019-11-01", 400000, None),
        ("E007", "黄丽", "销售部", "大客户经理", "huangli@company.com", "13800001007", "2021-03-15", 300000, "E006"),
        ("E008", "周杰", "人力资源部", "HR总监", "zhoujie@company.com", "13800001008", "2020-05-20", 380000, None),
        ("E009", "吴芳", "财务部", "财务总监", "wufang@company.com", "13800001009", "2019-08-01", 430000, None),
        ("E010", "孙鹏", "技术部", "后端工程师", "sunpeng@company.com", "13800001010", "2022-01-10", 260000, "E002"),
        ("E011", "马超", "技术部", "DevOps工程师", "machao@company.com", "13800001011", "2022-06-01", 270000, "E002"),
        ("E012", "林小红", "财务部", "会计", "linxh@company.com", "13800001012", "2021-09-01", 180000, "E009"),
    ]
    cursor.executemany(
        "INSERT INTO employees VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", employees_data
    )

    # ---- 插入部门数据 ----
    departments_data = [
        ("D001", "技术部", "E001", 5, 5000000),
        ("D002", "产品部", "E004", 2, 2000000),
        ("D003", "销售部", "E006", 2, 3500000),
        ("D004", "人力资源部", "E008", 1, 800000),
        ("D005", "财务部", "E009", 2, 1200000),
    ]
    cursor.executemany(
        "INSERT INTO departments VALUES (?, ?, ?, ?, ?)", departments_data
    )

    # ---- 插入项目数据 ----
    projects_data = [
        ("P001", "智能客服系统升级", "技术部", "张伟", "进行中", "2026-01-10", "2026-08-30", 5000000,
         "基于大语言模型的新一代智能客服系统，支持多轮对话和知识库检索"),
        ("P002", "ERP系统国产化迁移", "技术部", "李娜", "进行中", "2026-02-01", "2026-12-31", 8000000,
         "将现有Oracle ERP迁移至国产化平台，包括数据迁移、接口适配、性能优化"),
        ("P003", "客户数据平台CDP建设", "产品部", "陈刚", "规划中", "2026-06-01", "2026-11-30", 3000000,
         "构建统一的客户数据平台，实现客户360视图和精准营销"),
        ("P004", "网络安全等级保护2.0", "技术部", "孙鹏", "进行中", "2026-03-15", "2026-09-15", 2000000,
         "按照等保2.0标准完成公司核心系统的安全加固和测评"),
        ("P005", "移动办公平台V3.0", "产品部", "赵敏", "已完成", "2025-09-01", "2026-04-30", 1500000,
         "移动办公APP重大版本升级，新增AI助手、视频会议、文档协作功能"),
    ]
    cursor.executemany(
        "INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", projects_data
    )

    # ---- 插入销售数据 ----
    sales_data = [
        (1, "阿里巴巴集团", 5000000.00, "智能客服系统", "黄丽", "2026-01-15", "华东"),
        (2, "腾讯科技", 4500000.00, "数据分析平台", "黄丽", "2026-02-20", "华南"),
        (3, "华为技术", 8000000.00, "网络安全解决方案", "刘洋", "2026-03-10", "华南"),
        (4, "比亚迪股份", 3000000.00, "ERP系统", "黄丽", "2026-04-05", "华南"),
        (5, "中国石油", 2000000.00, "IT基础设施", "刘洋", "2026-04-20", "华北"),
        (6, "京东集团", 3500000.00, "移动办公平台", "黄丽", "2026-05-01", "华北"),
        (7, "字节跳动", 4000000.00, "推荐系统引擎", "刘洋", "2026-05-15", "华北"),
    ]
    cursor.executemany(
        "INSERT INTO sales VALUES (?, ?, ?, ?, ?, ?, ?)", sales_data
    )

    # ---- 插入库存数据 ----
    inventory_data = [
        ("I001", "服务器主机 Dell R750", "IT设备", 50, "台", 85000, "北京仓"),
        ("I002", "华为交换机 S6730", "网络设备", 120, "台", 35000, "上海仓"),
        ("I003", "ThinkPad X1 Carbon", "办公设备", 200, "台", 12000, "深圳仓"),
        ("I004", "Oracle数据库许可", "软件许可", 30, "套", 200000, "N/A"),
        ("I005", "防火墙设备 FortiGate", "安全设备", 40, "台", 65000, "北京仓"),
    ]
    cursor.executemany(
        "INSERT INTO inventory VALUES (?, ?, ?, ?, ?, ?, ?)", inventory_data
    )

    conn.commit()
    conn.close()
    log.info(f"✅ SQLite 数据库初始化完成: {DB_PATH}")
    log.info(f"   表: employees({len(employees_data)}行), departments({len(departments_data)}行), "
             f"projects({len(projects_data)}行), sales({len(sales_data)}行), inventory({len(inventory_data)}行)")


# ============================================================
# 2. 示例文档 - 用于向量数据库和关键词搜索
# ============================================================

SAMPLE_DOCUMENTS = [
    {
        "doc_id": "doc_001",
        "title": "2026年技术部年度规划",
        "content": (
            "2026年技术部年度规划概要："
            "1. 全面推系统容器化部署，目标将95%的服务迁移至Kubernetes集群。"
            "2. 建设企业级数据中台，统一数据标准，实现跨部门数据共享。"
            "3. 引入AI辅助开发工具，提升研发效能30%以上。"
            "4. 完成核心系统的微服务架构改造，提升系统可扩展性和可靠性。"
            "5. 建立完善的DevOps体系，实现CI/CD流水线覆盖率100%。"
            "6. 加强信息安全建设，通过ISO27001和等保2.0三级认证。"
        ),
        "source": "技术部",
        "tags": "年度规划,技术部,容器化,数据中台,AI,微服务,DevOps,信息安全"
    },
    {
        "doc_id": "doc_002",
        "title": "公司网络安全事件响应预案",
        "content": (
            "网络安全事件响应预案："
            "一级事件（特别重大）：核心业务系统中断超过30分钟，或客户数据泄露。"
            "需立即启动应急响应小组，由CTO担任总指挥，1小时内报告CEO。"
            "二级事件（重大）：非核心系统中断超过2小时，或内部数据异常访问。"
            "由安全部门负责人主导，4小时内形成初步报告。"
            "三级事件（一般）：钓鱼邮件攻击、单个终端病毒感染等。"
            "由IT运维团队处理，24小时内完成处置。"
            "所有安全事件必须在发现后15分钟内上报安全运营中心（SOC）。"
        ),
        "source": "信息安全部",
        "tags": "安全,应急预案,网络安全,事件响应"
    },
    {
        "doc_id": "doc_003",
        "title": "大数据平台技术选型报告",
        "content": (
            "大数据平台技术选型报告（2026年5月）："
            "经过POC测试，推荐以下技术栈："
            "数据处理：Apache Spark 3.5 + Delta Lake 3.0"
            "流处理：Apache Kafka 3.6 + Apache Flink 1.18"
            "数据仓库：ClickHouse（实时分析）+ Apache Doris（OLAP）"
            "数据治理：Apache Atlas + 自研数据质量平台"
            "调度系统：Apache DolphinScheduler 3.2"
            "BI工具：Apache Superset 3.0 + Metabase"
            "总预算估算：¥15,000,000（含硬件、软件许可、实施费用）"
        ),
        "source": "数据平台部",
        "tags": "大数据,技术选型,Spark,Kafka,Flink,ClickHouse"
    },
    {
        "doc_id": "doc_004",
        "title": "员工绩效考核管理办法V3.0",
        "content": (
            "员工绩效考核管理办法（2026版）："
            "考核周期：季度考核+年度综合评定。"
            "考核维度：工作业绩（50%）、专业能力（20%）、团队协作（15%）、创新贡献（15%）。"
            "评级分布：S级（卓越）≤10%、A级（优秀）≤20%、B级（良好）≥50%、"
            "C级（待改进）≥15%、D级（不合格）≤5%。"
            "连续两个季度C级或一次D级将进入PIP（绩效改进计划），为期60天。"
            "年度S级员工可获得额外3-6个月薪资的年终奖金。"
            "考核结果与晋升、调薪直接挂钩。"
        ),
        "source": "人力资源部",
        "tags": "绩效考核,HR,管理制度,晋升,考核"
    },
    {
        "doc_id": "doc_005",
        "title": "微服务架构设计规范",
        "content": (
            "微服务架构设计规范V2.0："
            "1. 服务拆分原则：按业务领域（Domain-Driven Design）拆分，每个服务只负责一个限界上下文。"
            "2. 服务间通信：同步调用使用gRPC（性能敏感）或RESTful API；异步通信使用Kafka。"
            "3. 数据管理：每个微服务拥有独立数据库，禁止跨服务直接访问数据库。"
            "4. 服务治理：使用Istio做服务网格，实现流量管理、熔断、限流、可观测性。"
            "5. 配置管理：使用Kubernetes ConfigMap + Vault管理配置和密钥。"
            "6. 监控告警：Prometheus + Grafana + AlertManager，SLI/SLO/SLA标准定义。"
            "7. 日志规范：结构化日志（JSON格式），统一使用ELK（Elasticsearch+Logstash+Kibana）收集。"
        ),
        "source": "技术架构组",
        "tags": "微服务,架构设计,规范,gRPC,Kafka,Istio,Kubernetes"
    },
    {
        "doc_id": "doc_006",
        "title": "2026年Q1销售业绩报告",
        "content": (
            "2026年第一季度销售业绩报告："
            "Q1总营收：¥23,500,000，同比增长35%，环比增长12%。"
            "新签客户：8家，其中VIP级客户2家（字节跳动、美团）。"
            "续约率：92%，较去年同期提升5个百分点。"
            "区域表现：华东区营收¥10,200,000（占比43%）、华南区¥7,800,000（33%）、"
            "华北区¥5,500,000（24%）。"
            "产品线表现：智能客服系统¥8,100,000（最佳）、数据分析平台¥6,300,000、"
            "网络安全解决方案¥5,200,000、ERP¥3,900,000。"
            "销售冠军：黄丽，个人贡献¥6,500,000。"
            "Q2展望：预计营收¥28,000,000-30,000,000，重点突破金融和医疗行业。"
        ),
        "source": "销售部",
        "tags": "销售,业绩报告,Q1,营收,客户,季度报告"
    },
    {
        "doc_id": "doc_007",
        "title": "公司数字化转型战略白皮书",
        "content": (
            "公司数字化转型战略白皮书（2026-2028）："
            "愿景：成为行业领先的数字化解决方案提供商。"
            "三大战略支柱："
            "1. 技术驱动：建设AI中台、数据中台、云原生基础设施，研发投入年增30%。"
            "2. 人才升级：引入AI/大数据/云计算高端人才，团队从200人扩充至500人。"
            "3. 生态构建：与阿里云、华为云深度合作，构建行业解决方案生态。"
            "关键里程碑：2026年底完成核心系统云原生改造；"
            "2027年中推出AI驱动的下一代产品矩阵；"
            "2028年实现年营收突破¥20亿。"
            "投资预算：三年总投入¥300,000,000（其中技术研发占60%）。"
        ),
        "source": "战略规划部",
        "tags": "数字化转型,战略,白皮书,AI,云原生,预算"
    },
]


def seed_documents():
    """创建示例文档文件"""
    log.info("=" * 50)
    log.info("📄 创建示例文档...")
    log.info("=" * 50)

    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

    for doc in SAMPLE_DOCUMENTS:
        filepath = DOCUMENTS_DIR / f"{doc['doc_id']}.txt"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"标题: {doc['title']}\n")
            f.write(f"来源: {doc['source']}\n")
            f.write(f"标签: {doc['tags']}\n")
            f.write(f"\n{doc['content']}\n")
        log.info(f"  创建: {filepath.name}")


# ============================================================
# 3. 示例代码文件
# ============================================================

SAMPLE_CODE_FILES = {
    "api_gateway.py": '''
"""
API 网关 - 统一入口服务
负责请求路由、认证鉴权、限流熔断
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import jwt
from typing import Optional

app = FastAPI(title="API Gateway", version="2.0.0")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 服务路由表
SERVICE_ROUTES = {
    "/api/users": "http://user-service:8001",
    "/api/orders": "http://order-service:8002",
    "/api/products": "http://product-service:8003",
    "/api/analytics": "http://analytics-service:8004",
}

JWT_SECRET = "enterprise-secret-key-2026"

async def verify_token(token: str) -> dict:
    """验证JWT Token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的Token")

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """认证中间件"""
    if request.url.path.startswith("/api/public"):
        return await call_next(request)

    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="缺少认证Token")

    payload = await verify_token(token)
    request.state.user = payload
    return await call_next(request)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0"}
''',

    "database_config.yaml": '''
# 数据库连接配置
# 适用于开发/测试/生产环境

development:
  mysql:
    host: 127.0.0.1
    port: 3306
    database: enterprise_dev
    username: dev_user
    password: dev_pass_2026
    pool_size: 10
    timeout: 30
  redis:
    host: 127.0.0.1
    port: 6379
    db: 0
    password: redis_dev_2026
  mongodb:
    uri: mongodb://localhost:27017/enterprise_dev

production:
  mysql:
    host: mysql-cluster.internal
    port: 3306
    database: enterprise_prod
    username: prod_user
    password: ${MYSQL_PASSWORD}
    pool_size: 50
    timeout: 60
    ssl: true
    ssl_ca: /etc/ssl/mysql-ca.pem
  redis:
    host: redis-cluster.internal
    port: 6379
    db: 0
    password: ${REDIS_PASSWORD}
    cluster_mode: true
  mongodb:
    uri: ${MONGO_URI}
    replica_set: rs0
''',

    "deployment.yaml": '''
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: enterprise
  labels:
    app: api-gateway
    version: v2.0.0
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
    spec:
      containers:
      - name: api-gateway
        image: registry.company.com/api-gateway:2.0.0
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: LOG_LEVEL
          value: "INFO"
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 2000m
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: api-gateway-svc
spec:
  type: ClusterIP
  selector:
    app: api-gateway
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
''',
}


def seed_code_samples():
    """创建示例代码文件"""
    log.info("=" * 50)
    log.info("💻 创建示例代码文件...")
    log.info("=" * 50)

    CODE_SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    for filename, content in SAMPLE_CODE_FILES.items():
        filepath = CODE_SAMPLES_DIR / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content.strip() + '\n')
        log.info(f"  创建: {filename}")


# ============================================================
# 4. 向量数据库 + 关键词索引初始化
# ============================================================

def seed_vector_db():
    """将文档添加到向量数据库"""
    log.info("=" * 50)
    log.info("🧠 初始化向量数据库...")
    log.info("=" * 50)

    from backends.vector_db import VectorDatabase

    vector_db = VectorDatabase()

    documents = [doc["content"] for doc in SAMPLE_DOCUMENTS]
    metadatas = [
        {"source": doc["source"], "title": doc["title"], "tags": doc["tags"]}
        for doc in SAMPLE_DOCUMENTS
    ]
    ids = [doc["doc_id"] for doc in SAMPLE_DOCUMENTS]

    vector_db.add_documents(documents, metadatas, ids)
    log.info(f"✅ 向量数据库: 已添加 {len(documents)} 个文档")


def seed_keyword_index():
    """将文档添加到关键词搜索索引"""
    log.info("=" * 50)
    log.info("🔍 初始化关键词搜索索引...")
    log.info("=" * 50)

    from backends.keyword_search import KeywordSearchEngine

    keyword_engine = KeywordSearchEngine()
    keyword_engine.rebuild_index()  # 清空重建

    keyword_engine.index_documents(SAMPLE_DOCUMENTS)
    log.info(f"✅ 关键词索引: 已索引 {len(SAMPLE_DOCUMENTS)} 个文档")


# ============================================================
# 主入口
# ============================================================

def main():
    """运行所有数据初始化"""
    log.info("=" * 60)
    log.info("🚀 开始初始化所有数据源...")
    log.info("=" * 60)

    try:
        seed_database()
    except Exception as e:
        log.error(f"数据库初始化失败: {e}")

    try:
        seed_documents()
    except Exception as e:
        log.error(f"文档创建失败: {e}")

    try:
        seed_code_samples()
    except Exception as e:
        log.error(f"代码示例创建失败: {e}")

    try:
        seed_vector_db()
    except Exception as e:
        log.error(f"向量数据库初始化失败: {e}")
        log.info("提示: 向量数据库需要安装 sentence-transformers 和 chromadb")
        log.info("      pip install sentence-transformers chromadb")

    try:
        seed_keyword_index()
    except Exception as e:
        log.error(f"关键词索引初始化失败: {e}")
        log.info("提示: 关键词搜索需要安装 whoosh 和 jieba")
        log.info("      pip install whoosh jieba")

    log.info("=" * 60)
    log.info("✅ 所有数据初始化完成！")
    log.info("=" * 60)
    log.info(f"  SQLite数据库: {DB_PATH}")
    log.info(f"  文档目录: {DOCUMENTS_DIR}")
    log.info(f"  代码目录: {CODE_SAMPLES_DIR}")
    log.info(f"  向量数据库: {DATA_DIR / 'vector_db'}")
    log.info(f"  关键词索引: {DATA_DIR / 'keyword_index'}")


if __name__ == "__main__":
    main()
