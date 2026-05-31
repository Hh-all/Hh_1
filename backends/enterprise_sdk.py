"""
============================================================
模拟企业内部系统 SDK - 企业信息化系统模拟
Simulated Enterprise Internal System SDK
============================================================

模拟企业内部常见的信息化系统：
- HR 系统（员工信息、组织架构）
- CRM 系统（客户关系、销售机会）
- ERP 系统（库存、采购订单）
- KM 系统（知识库、规章制度）
"""
import json
import time
import random
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from logger_setup import log


# ============================================================
# 数据模型
# ============================================================

@dataclass
class Employee:
    id: str
    name: str
    department: str
    position: str
    email: str
    phone: str
    hire_date: str
    manager_id: str = ""

@dataclass
class Customer:
    id: str
    name: str
    industry: str
    contact_person: str
    phone: str
    level: str  # VIP / A / B / C
    total_revenue: float
    status: str  # active / inactive / prospect

@dataclass
class InventoryItem:
    id: str
    name: str
    category: str
    quantity: int
    unit: str
    unit_price: float
    warehouse: str
    last_updated: str

@dataclass
class Project:
    id: str
    name: str
    owner: str
    department: str
    status: str
    start_date: str
    end_date: str
    budget: float
    description: str


# ============================================================
# 模拟企业数据
# ============================================================

MOCK_EMPLOYEES = [
    Employee("E001", "张伟", "技术部", "技术总监", "zhangwei@company.com", "13800001001", "2020-01-15"),
    Employee("E002", "李娜", "技术部", "高级工程师", "lina@company.com", "13800001002", "2020-03-20", "E001"),
    Employee("E003", "王磊", "技术部", "前端工程师", "wanglei@company.com", "13800001003", "2021-06-01", "E002"),
    Employee("E004", "赵敏", "产品部", "产品总监", "zhaomin@company.com", "13800001004", "2020-02-10"),
    Employee("E005", "陈刚", "产品部", "产品经理", "chengang@company.com", "13800001005", "2021-01-05", "E004"),
    Employee("E006", "刘洋", "销售部", "销售总监", "liuyang@company.com", "13800001006", "2019-11-01"),
    Employee("E007", "黄丽", "销售部", "大客户经理", "huangli@company.com", "13800001007", "2021-03-15", "E006"),
    Employee("E008", "周杰", "人力资源部", "HR总监", "zhoujie@company.com", "13800001008", "2020-05-20"),
    Employee("E009", "吴芳", "财务部", "财务总监", "wufang@company.com", "13800001009", "2019-08-01"),
    Employee("E010", "孙鹏", "技术部", "后端工程师", "sunpeng@company.com", "13800001010", "2022-01-10", "E002"),
]

MOCK_CUSTOMERS = [
    Customer("C001", "阿里巴巴集团", "互联网", "马云", "0571-88888888", "VIP", 5000000.00, "active"),
    Customer("C002", "腾讯科技", "互联网", "马化腾", "0755-88888888", "VIP", 4500000.00, "active"),
    Customer("C003", "华为技术", "通信", "任正非", "0755-99999999", "VIP", 8000000.00, "active"),
    Customer("C004", "比亚迪股份", "新能源", "王传福", "0755-77777777", "A", 3000000.00, "active"),
    Customer("C005", "中国石油", "能源", "戴厚良", "010-88888888", "A", 2000000.00, "active"),
    Customer("C006", "中国移动", "通信", "杨杰", "010-66666666", "B", 1500000.00, "active"),
    Customer("C007", "京东集团", "电商", "刘强东", "010-55555555", "A", 3500000.00, "active"),
    Customer("C008", "字节跳动", "互联网", "张一鸣", "010-44444444", "A", 4000000.00, "active"),
    Customer("C009", "美团点评", "互联网", "王兴", "010-33333333", "B", 1800000.00, "active"),
    Customer("C010", "小米科技", "消费电子", "雷军", "010-22222222", "B", 2200000.00, "active"),
]

MOCK_INVENTORY = [
    InventoryItem("I001", "服务器主机 Dell R750", "IT设备", 50, "台", 85000, "北京仓", "2026-05-15"),
    InventoryItem("I002", "华为交换机 S6730", "网络设备", 120, "台", 35000, "上海仓", "2026-05-10"),
    InventoryItem("I003", "ThinkPad X1 Carbon", "办公设备", 200, "台", 12000, "深圳仓", "2026-04-28"),
    InventoryItem("I004", "Oracle数据库许可", "软件许可", 30, "套", 200000, "N/A", "2026-03-01"),
    InventoryItem("I005", "防火墙设备 FortiGate", "安全设备", 40, "台", 65000, "北京仓", "2026-05-20"),
    InventoryItem("I006", "UPS不间断电源", "基础设施", 80, "台", 15000, "上海仓", "2026-04-15"),
    InventoryItem("I007", "光纤跳线 LC-LC", "网络配件", 500, "根", 50, "深圳仓", "2026-05-01"),
    InventoryItem("I008", "DDR5 64GB 内存条", "IT配件", 300, "条", 2800, "北京仓", "2026-05-10"),
]

MOCK_PROJECTS = [
    Project("P001", "智能客服系统升级", "张伟", "技术部", "进行中", "2026-01-10", "2026-08-30", 5000000,
            "基于大语言模型的新一代智能客服系统，支持多轮对话和知识库检索"),
    Project("P002", "ERP系统国产化迁移", "李娜", "技术部", "进行中", "2026-02-01", "2026-12-31", 8000000,
            "将现有Oracle ERP迁移至国产化平台，包括数据迁移、接口适配、性能优化"),
    Project("P003", "客户数据平台CDP建设", "陈刚", "产品部", "规划中", "2026-06-01", "2026-11-30", 3000000,
            "构建统一的客户数据平台，实现客户360视图和精准营销"),
    Project("P004", "网络安全等级保护2.0", "孙鹏", "技术部", "进行中", "2026-03-15", "2026-09-15", 2000000,
            "按照等保2.0标准完成公司核心系统的安全加固和测评"),
    Project("P005", "移动办公平台V3.0", "赵敏", "产品部", "已完成", "2025-09-01", "2026-04-30", 1500000,
            "移动办公APP重大版本升级，新增AI助手、视频会议、文档协作功能"),
]

MOCK_KNOWLEDGE_ARTICLES = [
    {
        "id": "K001", "title": "员工入职流程指南", "category": "HR制度",
        "content": "新员工入职流程：1. 提交入职材料（身份证、学历证书、离职证明）；"
                   "2. 签订劳动合同（试用期3-6个月）；3. 领取办公设备；4. 参加新员工培训；"
                   "5. 部门报到。入职后30天内办理社保和公积金。"
    },
    {
        "id": "K002", "title": "差旅费用报销制度", "category": "财务制度",
        "content": "差旅报销标准：一线城市住宿标准500元/天，二线城市350元/天，其他城市250元/天。"
                   "交通：高铁二等座、飞机经济舱。餐补：100元/天。出差申请需提前3个工作日提交。"
                   "报销需在出差结束后15个工作日内提交。"
    },
    {
        "id": "K003", "title": "信息系统安全管理制度", "category": "安全制度",
        "content": "信息安全管理制度要点：1. 所有系统必须启用双因素认证；2. 密码长度不少于12位，"
                   "包含大小写字母、数字和特殊字符；3. 禁止使用个人设备连接公司内网；"
                   "4. 数据导出需经部门主管审批；5. 离职员工账号需在当天内注销。"
    },
    {
        "id": "K004", "title": "技术架构规范V2.0", "category": "技术规范",
        "content": "公司技术架构规范：后端使用Java Spring Boot / Python FastAPI；"
                   "前端使用React / Vue3；数据库MySQL + Redis缓存；消息队列Kafka；"
                   "容器化部署Kubernetes；CI/CD使用GitLab CI；代码审查覆盖率要求>80%。"
                   "API设计遵循RESTful规范，使用OpenAPI 3.0文档。"
    },
    {
        "id": "K005", "title": "采购审批流程", "category": "业务流程",
        "content": "采购审批流程：金额<1万元由部门主管审批；1-10万元需部门主管+财务总监审批；"
                   "10-50万元需部门主管+财务总监+VP审批；>50万元需CEO审批。"
                   "所有IT设备采购还需IT部门技术评审。单次采购金额超过100万元需招标。"
    },
]


# ============================================================
# 企业系统 SDK
# ============================================================

class HRSystem:
    """人力资源管理系统模拟"""

    def query_employee(self, name_or_id: str) -> str:
        """查询员工信息"""
        log.info(f"[HR系统] 查询员工: {name_or_id}")
        results = []
        for emp in MOCK_EMPLOYEES:
            if name_or_id.lower() in emp.name.lower() or name_or_id.upper() == emp.id.upper():
                results.append(
                    f"员工ID: {emp.id} | 姓名: {emp.name} | 部门: {emp.department} | "
                    f"职位: {emp.position}\n  邮箱: {emp.email} | 电话: {emp.phone} | "
                    f"入职日期: {emp.hire_date}"
                )
        if not results:
            return f"未找到与 '{name_or_id}' 匹配的员工。"
        return "员工查询结果:\n" + "\n".join(results)

    def query_department(self, dept_name: str) -> str:
        """查询部门信息"""
        log.info(f"[HR系统] 查询部门: {dept_name}")
        members = [e for e in MOCK_EMPLOYEES if dept_name in e.department]
        if not members:
            return f"未找到部门 '{dept_name}'。"

        lines = [f"部门: {dept_name}（共 {len(members)} 人）"]
        # 构建组织架构
        managers = [e for e in members if not e.manager_id or e.manager_id not in [m.id for m in members]]
        for mgr in managers:
            lines.append(f"  ├─ {mgr.name} ({mgr.position})")
            for sub in members:
                if sub.manager_id == mgr.id:
                    lines.append(f"  │   └─ {sub.name} ({sub.position})")
        return "\n".join(lines)

    def get_all_departments(self) -> str:
        """获取所有部门列表"""
        depts = list(set(e.department for e in MOCK_EMPLOYEES))
        lines = ["公司部门列表:"]
        for i, dept in enumerate(sorted(depts), 1):
            count = len([e for e in MOCK_EMPLOYEES if e.department == dept])
            lines.append(f"  {i}. {dept}（{count}人）")
        return "\n".join(lines)


class CRMSystem:
    """客户关系管理系统模拟"""

    def query_customer(self, name_or_id: str) -> str:
        """查询客户信息"""
        log.info(f"[CRM系统] 查询客户: {name_or_id}")
        results = []
        for cust in MOCK_CUSTOMERS:
            if name_or_id.lower() in cust.name.lower() or name_or_id.upper() == cust.id.upper():
                results.append(
                    f"客户ID: {cust.id} | 名称: {cust.name} | 行业: {cust.industry}\n"
                    f"  联系人: {cust.contact_person} | 电话: {cust.phone} | "
                    f"等级: {cust.level} | 累计营收: ¥{cust.total_revenue:,.0f} | 状态: {cust.status}"
                )
        if not results:
            return f"未找到与 '{name_or_id}' 匹配的客户。"
        return "客户查询结果:\n" + "\n".join(results)

    def list_by_level(self, level: str = "VIP") -> str:
        """按客户等级列出"""
        customers = [c for c in MOCK_CUSTOMERS if c.level.upper() == level.upper()]
        lines = [f"{level}级客户（共 {len(customers)} 家）:"]
        for c in customers:
            lines.append(f"  {c.name} | {c.industry} | 累计营收: ¥{c.total_revenue:,.0f}")
        return "\n".join(lines)

    def get_pipeline(self) -> str:
        """获取销售管道概览"""
        total = sum(c.total_revenue for c in MOCK_CUSTOMERS if c.status == "active")
        by_level = {}
        for c in MOCK_CUSTOMERS:
            by_level[c.level] = by_level.get(c.level, 0) + c.total_revenue

        lines = ["销售管道概览:",
                 f"  活跃客户总营收: ¥{total:,.0f}",
                 f"  活跃客户数: {len([c for c in MOCK_CUSTOMERS if c.status == 'active'])}"]
        for lvl in ["VIP", "A", "B", "C"]:
            if lvl in by_level:
                lines.append(f"  {lvl}级客户营收: ¥{by_level[lvl]:,.0f}")
        return "\n".join(lines)


class ERPSystem:
    """企业资源计划系统模拟"""

    def query_inventory(self, item_name: str) -> str:
        """查询库存"""
        log.info(f"[ERP系统] 查询库存: {item_name}")
        results = []
        for item in MOCK_INVENTORY:
            if item_name.lower() in item.name.lower() or item_name.upper() == item.id.upper():
                total_value = item.quantity * item.unit_price
                results.append(
                    f"物料ID: {item.id} | 名称: {item.name} | 类别: {item.category}\n"
                    f"  库存: {item.quantity}{item.unit} | 单价: ¥{item.unit_price:,} | "
                    f"总价值: ¥{total_value:,} | 仓库: {item.warehouse}"
                )
        if not results:
            return f"未找到与 '{item_name}' 匹配的库存物料。"
        return "库存查询结果:\n" + "\n".join(results)

    def list_by_warehouse(self, warehouse: str) -> str:
        """按仓库列出库存"""
        items = [i for i in MOCK_INVENTORY if warehouse in i.warehouse]
        if not items:
            return f"未找到仓库 '{warehouse}'。"
        lines = [f"仓库: {warehouse}（{len(items)} 种物料）:"]
        for item in items:
            lines.append(f"  {item.name} | {item.quantity}{item.unit} | ¥{item.unit_price:,}/件")
        return "\n".join(lines)

    def get_inventory_summary(self) -> str:
        """库存总览"""
        total_value = sum(i.quantity * i.unit_price for i in MOCK_INVENTORY)
        lines = ["库存总览:",
                 f"  物料种类: {len(MOCK_INVENTORY)} 种",
                 f"  库存总价值: ¥{total_value:,.0f}"]
        by_cat = {}
        for i in MOCK_INVENTORY:
            by_cat[i.category] = by_cat.get(i.category, 0) + i.quantity * i.unit_price
        for cat, val in sorted(by_cat.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {cat}: ¥{val:,.0f}")
        return "\n".join(lines)


class KnowledgeManagement:
    """知识管理系统模拟"""

    def search(self, query: str) -> str:
        """搜索知识库文章"""
        log.info(f"[知识管理] 搜索: {query}")
        results = []
        for article in MOCK_KNOWLEDGE_ARTICLES:
            score = 0
            if query.lower() in article["title"].lower():
                score += 3
            if query.lower() in article["content"].lower():
                score += 1
            if query.lower() in article["category"].lower():
                score += 2
            if score > 0:
                results.append((score, article))

        results.sort(key=lambda x: x[0], reverse=True)

        if not results:
            return f"知识库中未找到与 '{query}' 相关的文章。"

        lines = [f"知识库搜索结果（共 {len(results)} 篇相关文章）:"]
        for score, article in results:
            lines.append(f"\n  [{article['category']}] {article['title']}")
            lines.append(f"  {article['content'][:200]}...")
        return "\n".join(lines)

    def list_categories(self) -> str:
        """列出知识库分类"""
        cats = list(set(a["category"] for a in MOCK_KNOWLEDGE_ARTICLES))
        lines = ["知识库分类:"]
        for cat in sorted(cats):
            count = len([a for a in MOCK_KNOWLEDGE_ARTICLES if a["category"] == cat])
            lines.append(f"  {cat}（{count} 篇）")
        return "\n".join(lines)


# ============================================================
# 统一的企业 SDK 入口
# ============================================================

class EnterpriseSDK:
    """
    模拟企业内部系统 SDK - 统一入口

    将 HR、CRM、ERP、知识库等系统封装为统一接口，
    供搜索代理调用。
    """

    def __init__(self):
        self.hr = HRSystem()
        self.crm = CRMSystem()
        self.erp = ERPSystem()
        self.km = KnowledgeManagement()
        log.info("[企业SDK] 已初始化所有子系统 (HR/CRM/ERP/KM)")

    def query(self, query: str) -> str:
        """
        智能路由查询到相应的子系统。

        根据查询内容的关键词自动判断应该查询哪个系统：
        - 员工/部门/人事 → HR
        - 客户/销售/营收 → CRM
        - 库存/物料/仓库 → ERP
        - 制度/流程/规范 → 知识库

        Args:
            query: 自然语言查询

        Returns:
            查询结果
        """
        log.info(f"[企业SDK] 智能路由查询: {query[:100]}...")

        results = []

        # HR 相关关键词
        hr_keywords = ["员工", "部门", "人事", "职位", "入职", "离职", "同事", "组织架构", "谁", "联系方式",
                       "电话", "邮箱", "总监", "经理", "工程师"]
        if any(kw in query for kw in hr_keywords):
            # 尝试提取人名或部门名
            results.append(self._route_hr(query))

        # CRM 相关关键词
        crm_keywords = ["客户", "销售", "营收", "订单", "合作", "伙伴", "VIP", "客户关系"]
        if any(kw in query for kw in crm_keywords):
            results.append(self._route_crm(query))

        # ERP 相关关键词
        erp_keywords = ["库存", "物料", "仓库", "采购", "设备", "硬件", "软件许可", "资产", "服务器", "交换机", "电脑"]
        if any(kw in query for kw in erp_keywords):
            results.append(self._route_erp(query))

        # 知识库相关关键词
        km_keywords = ["制度", "流程", "规范", "规定", "标准", "指南", "怎么", "如何", "流程",
                       "报销", "安全", "密码", "入职流程", "审批"]
        if any(kw in query for kw in km_keywords):
            results.append(self._route_km(query))

        # 项目相关
        if "项目" in query:
            results.append(self._query_projects(query))

        if not results:
            # 如果没有任何匹配，返回所有系统的概述
            return self._get_overview(query)

        return "\n\n---\n\n".join(results)

    def _route_hr(self, query: str) -> str:
        """路由到HR系统"""
        # 尝试找出具体的人名
        for emp in MOCK_EMPLOYEES:
            if emp.name in query:
                return self.hr.query_employee(emp.name)

        # 尝试找出部门名
        dept_names = list(set(e.department for e in MOCK_EMPLOYEES))
        for dept in dept_names:
            if dept in query:
                return self.hr.query_department(dept)

        # 部门列表请求
        if "部门" in query and ("哪些" in query or "所有" in query or "列表" in query):
            return self.hr.get_all_departments()

        return self.hr.get_all_departments()

    def _route_crm(self, query: str) -> str:
        """路由到CRM系统"""
        for cust in MOCK_CUSTOMERS:
            if cust.name in query:
                return self.crm.query_customer(cust.name)

        if "VIP" in query.upper():
            return self.crm.list_by_level("VIP")

        return self.crm.get_pipeline()

    def _route_erp(self, query: str) -> str:
        """路由到ERP系统"""
        for item in MOCK_INVENTORY:
            if item.name in query:
                return self.erp.query_inventory(item.name)

        warehouse_names = ["北京仓", "上海仓", "深圳仓"]
        for wh in warehouse_names:
            if wh in query:
                return self.erp.list_by_warehouse(wh)

        return self.erp.get_inventory_summary()

    def _route_km(self, query: str) -> str:
        """路由到知识库"""
        # 提取可能的搜索词
        for kw in ["入职", "报销", "安全", "架构", "采购", "审批"]:
            if kw in query:
                return self.km.search(kw)
        return self.km.search(query)

    def _query_projects(self, query: str) -> str:
        """查询项目信息"""
        results = []
        for proj in MOCK_PROJECTS:
            if any(kw in query for kw in [proj.name, proj.id, proj.owner, proj.department]):
                results.append(proj)

        # 按状态匹配
        status_map = {"进行中": "进行中", "规划中": "规划中", "已完成": "已完成", "完成": "已完成"}
        for kw, status in status_map.items():
            if kw in query:
                results = [p for p in MOCK_PROJECTS if p.status == status]
                break

        if not results:
            results = MOCK_PROJECTS

        lines = [f"项目查询结果（共 {len(results)} 个项目）:"]
        for p in results:
            lines.append(f"\n  [{p.status}] {p.name} (ID: {p.id})")
            lines.append(f"  负责人: {p.owner} | 部门: {p.department} | "
                         f"预算: ¥{p.budget:,} | 周期: {p.start_date} ~ {p.end_date}")
            lines.append(f"  描述: {p.description}")
        return "\n".join(lines)

    def _get_overview(self, query: str) -> str:
        """无法精确匹配时返回概览"""
        return (
            f"关于 '{query}' 未找到精确匹配。以下是企业系统概览:\n\n"
            f"{self.hr.get_all_departments()}\n\n"
            f"{self.erp.get_inventory_summary()}\n\n"
            f"{self.km.list_categories()}"
        )
