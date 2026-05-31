"""
主窗口 - 桌面聊天应用界面
Main Window with Modern Chat Interface
"""
import sys
import os
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QScrollArea, QLabel, QFrame, QSplitter,
    QSizePolicy, QMenuBar, QMenu, QMessageBox, QLineEdit, QDialog,
    QFormLayout, QDialogButtonBox, QGroupBox
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QThread
from PySide6.QtGui import QFont, QColor, QPalette, QAction, QTextCursor, QIcon

# 确保项目根目录可 import
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DOUBAO_API_KEY, DOUBAO_MODEL, DOUBAO_BASE_URL, MAX_SEARCH_ITERATIONS
from .agent_worker import AgentWorker


# ================================================================
# 样式表 - 现代暗色主题
# ================================================================

STYLE_DARK = """
QMainWindow {
    background-color: #1a1a2e;
}
QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
}
QScrollArea {
    border: none;
    background-color: #16213e;
}
QScrollBar:vertical {
    background: #16213e;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #0f3460;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QLineEdit, QTextEdit {
    background-color: #0f3460;
    border: 1px solid #533483;
    border-radius: 8px;
    padding: 8px 12px;
    color: #e0e0e0;
    font-size: 13px;
}
QLineEdit:focus, QTextEdit:focus {
    border-color: #e94560;
}
QPushButton {
    background-color: #e94560;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 20px;
    font-weight: bold;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #ff6b81;
}
QPushButton:pressed {
    background-color: #c23152;
}
QPushButton:disabled {
    background-color: #555;
    color: #999;
}
QFrame#statusBar {
    background-color: #16213e;
    border-top: 1px solid #533483;
    padding: 4px 12px;
}
QLabel#statusLabel {
    color: #888;
    font-size: 11px;
}
QGroupBox {
    border: 1px solid #533483;
    border-radius: 6px;
    margin-top: 8px;
    padding-top: 16px;
    font-weight: bold;
    color: #e94560;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
}
QMenuBar {
    background-color: #16213e;
    border-bottom: 1px solid #533483;
}
QMenuBar::item:selected {
    background-color: #e94560;
}
QMenu {
    background-color: #1a1a2e;
    border: 1px solid #533483;
}
QMenu::item:selected {
    background-color: #e94560;
}
"""


# ================================================================
# 自定义消息组件
# ================================================================

class ChatMessage(QFrame):
    """单条聊天消息"""

    def __init__(self, role: str, content: str = "", parent=None):
        super().__init__(parent)
        self.role = role
        self.setObjectName(f"msg_{role}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        # 角色标签
        role_label = QLabel({
            "user": "🧑 你",
            "thinking": "🧠 Doubao 思考",
            "tool": "🔧 工具调用",
            "answer": "🤖 Doubao 回答",
            "system": "📋 系统",
        }.get(role, role))
        role_label.setStyleSheet(f"color: {'#e94560' if role == 'user' else '#4ecdc4' if role == 'answer' else '#ffd93d' if role == 'tool' else '#6c5ce7' if role == 'thinking' else '#888'}; font-weight: bold; font-size: 11px;")
        layout.addWidget(role_label)

        # 内容
        self.content_label = QLabel(content)
        self.content_label.setWordWrap(True)
        self.content_label.setTextFormat(Qt.MarkdownText)
        self.content_label.setStyleSheet("color: #e0e0e0; padding: 4px 0;")
        layout.addWidget(self.content_label)

        # 样式按角色区分
        if role == "user":
            self.setStyleSheet("""
                ChatMessage#msg_user {
                    background-color: #2d1b3d;
                    border-left: 3px solid #e94560;
                    border-radius: 4px;
                    margin: 4px 40px 4px 8px;
                }
            """)
        elif role == "answer":
            self.setStyleSheet("""
                ChatMessage#msg_answer {
                    background-color: #1a3a2a;
                    border-left: 3px solid #4ecdc4;
                    border-radius: 4px;
                    margin: 4px 8px 4px 8px;
                }
            """)
        elif role == "tool":
            self.setStyleSheet("""
                ChatMessage#msg_tool {
                    background-color: #2d2d1b;
                    border-left: 3px solid #ffd93d;
                    border-radius: 4px;
                    margin: 4px 8px 4px 40px;
                }
            """)
        elif role == "thinking":
            self.setStyleSheet("""
                ChatMessage#msg_thinking {
                    background-color: #1b1b3d;
                    border-left: 3px solid #6c5ce7;
                    border-radius: 4px;
                    margin: 4px 8px 4px 20px;
                    font-style: italic;
                }
            """)
        else:
            self.setStyleSheet("""
                ChatMessage {
                    background-color: transparent;
                    margin: 2px 8px;
                }
            """)

    def update_content(self, new_content: str):
        self.content_label.setText(new_content)


# ================================================================
# 主窗口
# ================================================================

class MainWindow(QMainWindow):
    """智能搜索代理 - 桌面应用主窗口"""

    def __init__(self):
        super().__init__()
        self.worker: AgentWorker | None = None
        self.messages: list[ChatMessage] = []
        self._setup_ui()
        self._setup_menu()
        self._show_welcome()

    def _setup_ui(self):
        """构建 UI 布局"""
        self.setWindowTitle("🔍 企业智能搜索代理 - Agentic Search")
        self.setMinimumSize(900, 650)
        self.resize(1000, 720)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ---- 顶部标题栏 ----
        title_bar = QFrame()
        title_bar.setStyleSheet("background-color: #16213e; padding: 8px 16px; border-bottom: 1px solid #533483;")
        title_layout = QHBoxLayout(title_bar)
        title_label = QLabel("🔍 企业智能搜索代理")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #e94560; border: none; background: transparent;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        self.status_indicator = QLabel("● 就绪")
        self.status_indicator.setStyleSheet("color: #4ecdc4; font-size: 12px; border: none; background: transparent;")
        title_layout.addWidget(self.status_indicator)

        main_layout.addWidget(title_bar)

        # ---- 聊天区域 ----
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_layout.setSpacing(2)
        self.chat_layout.addStretch()

        self.scroll_area.setWidget(self.chat_container)
        main_layout.addWidget(self.scroll_area, stretch=1)

        # ---- 输入区域 ----
        input_frame = QFrame()
        input_frame.setStyleSheet("background-color: #16213e; border-top: 1px solid #533483; padding: 10px 16px;")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(0, 0, 0, 0)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("输入你的问题，Doubao 会自动选择最佳搜索策略...")
        self.input_field.setMinimumHeight(38)
        self.input_field.returnPressed.connect(self._send_message)
        input_layout.addWidget(self.input_field, stretch=1)

        self.send_btn = QPushButton("发送")
        self.send_btn.setMinimumHeight(38)
        self.send_btn.setMinimumWidth(80)
        self.send_btn.clicked.connect(self._send_message)
        input_layout.addWidget(self.send_btn)

        main_layout.addWidget(input_frame)

        # ---- 状态栏 ----
        status_frame = QFrame(objectName="statusBar")
        status_frame.setStyleSheet("background-color: #16213e; border-top: 1px solid #533483; padding: 4px 12px;")
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(8, 2, 8, 2)
        self.status_text = QLabel("就绪 — 输入问题开始搜索")
        self.status_text.setStyleSheet("color: #888; font-size: 11px; border: none; background: transparent;")
        status_layout.addWidget(self.status_text)
        main_layout.addWidget(status_frame)

    def _setup_menu(self):
        """设置菜单栏"""
        menu_bar = self.menuBar()

        # 文件菜单
        file_menu = menu_bar.addMenu("文件")
        clear_action = QAction("清空对话", self)
        clear_action.triggered.connect(self._clear_chat)
        file_menu.addAction(clear_action)
        file_menu.addSeparator()
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 设置菜单
        settings_menu = menu_bar.addMenu("设置")
        config_action = QAction("API 配置", self)
        config_action.triggered.connect(self._open_settings)
        settings_menu.addAction(config_action)

        # 帮助菜单
        help_menu = menu_bar.addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    # ================================================================
    # 事件处理
    # ================================================================

    def _send_message(self):
        """发送用户消息，启动搜索代理"""
        query = self.input_field.text().strip()
        if not query:
            return

        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "请等待", "正在处理上一个问题，请稍候...")
            return

        # 如果还没配 API Key
        if DOUBAO_API_KEY == "your-api-key-here":
            self._add_system_message("⚠️ 请先配置 Doubao API Key！点击菜单 → 设置 → API 配置")
            self._open_settings()
            return

        # 禁用输入
        self.input_field.setEnabled(False)
        self.send_btn.setEnabled(False)
        self.status_indicator.setText("● 搜索中...")
        self.status_indicator.setStyleSheet("color: #ffd93d; font-size: 12px; border: none; background: transparent;")

        # 显示用户消息
        self._add_user_message(query)
        self.input_field.clear()

        # 启动后台工作线程
        self.worker = AgentWorker(query)
        self.worker.tool_call.connect(self._on_tool_call)
        self.worker.tool_result.connect(self._on_tool_result)
        self.worker.answer_ready.connect(self._on_answer)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_tool_call(self, tool_name: str, query: str):
        """收到工具调用信号"""
        tool_names_map = {
            "search_local_database": "📊 本地数据库",
            "search_vector_database": "🧠 向量语义搜索",
            "search_keywords": "🔍 关键词搜索",
            "search_code_repository": "💻 代码仓库",
            "query_enterprise_system": "🏢 企业系统",
        }
        display_name = tool_names_map.get(tool_name, tool_name)
        self._add_tool_message(f"**{display_name}**\n\n查询: _{query}_\n\n⏳ 搜索中...")

    def _on_tool_result(self, tool_name: str, preview: str, elapsed: str):
        """收到工具结果信号"""
        # 更新最近一条 tool 消息
        for msg in reversed(self.messages):
            if msg.role == "tool" and "搜索中" in msg.content_label.text():
                msg.update_content(msg.content_label.text().replace("⏳ 搜索中...", f"✅ 找到结果 ({len(preview)} 字符)"))
                break

    def _on_answer(self, answer: str):
        """收到最终答案"""
        self._add_answer_message(answer)
        self.status_text.setText("搜索完成")

    def _on_finished(self, stats: str):
        """搜索完成"""
        self.input_field.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.status_indicator.setText("● 就绪")
        self.status_indicator.setStyleSheet("color: #4ecdc4; font-size: 12px; border: none; background: transparent;")
        self.status_text.setText("就绪 — 输入新问题继续搜索")

    def _on_error(self, error_msg: str):
        """搜索出错"""
        self._add_system_message(f"❌ 搜索出错: {error_msg}")
        self.input_field.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.status_indicator.setText("● 就绪")
        self.status_indicator.setStyleSheet("color: #4ecdc4; font-size: 12px; border: none; background: transparent;")

    # ================================================================
    # 消息管理
    # ================================================================

    def _add_user_message(self, text: str):
        msg = ChatMessage("user", text)
        self._append_message(msg)

    def _add_answer_message(self, text: str):
        msg = ChatMessage("answer", text)
        self._append_message(msg)

    def _add_tool_message(self, text: str):
        msg = ChatMessage("tool", text)
        self._append_message(msg)

    def _add_system_message(self, text: str):
        msg = ChatMessage("system", text)
        self._append_message(msg)

    def _append_message(self, msg: ChatMessage):
        # 移除 stretch
        if self.chat_layout.count() > 0:
            item = self.chat_layout.itemAt(self.chat_layout.count() - 1)
            if item.spacerItem():
                self.chat_layout.removeItem(item)

        self.chat_layout.addWidget(msg)
        self.messages.append(msg)
        self.chat_layout.addStretch()

        # 自动滚动到底部
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _show_welcome(self):
        """显示欢迎消息"""
        self._add_system_message(
            "👋 **欢迎使用企业智能搜索代理**\n\n"
            "我可以帮你搜索以下数据源：\n\n"
            "- 📊 **本地数据库** — 员工、项目、销售等结构化数据\n"
            "- 🧠 **向量语义搜索** — 文档、知识的语义匹配\n"
            "- 🔍 **关键词搜索** — 全文关键词精确检索\n"
            "- 💻 **代码仓库** — 源代码和配置文件搜索\n"
            "- 🏢 **企业系统** — HR、CRM、ERP、知识库\n\n"
            "只需在下方输入问题，Doubao 会自动选择最佳搜索策略！"
        )

    def _clear_chat(self):
        """清空所有消息"""
        for msg in self.messages:
            self.chat_layout.removeWidget(msg)
            msg.deleteLater()
        self.messages.clear()
        self._show_welcome()

    # ================================================================
    # 对话框
    # ================================================================

    def _open_settings(self):
        """打开设置对话框"""
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.Accepted:
            values = dialog.get_values()
            # 更新运行时配置
            import config
            config.DOUBAO_API_KEY = values["api_key"]
            config.DOUBAO_MODEL = values["model"]
            config.MAX_SEARCH_ITERATIONS = int(values["max_iterations"])

            # 更新 .env 文件
            env_path = Path(__file__).parent.parent / ".env"
            self._update_env_file(env_path, values)

            QMessageBox.information(self, "配置已保存", "新配置已生效！")

    def _update_env_file(self, path: Path, values: dict):
        """更新 .env 配置文件"""
        if not path.exists():
            return
        content = path.read_text(encoding="utf-8")
        replacements = {
            r"DOUBAO_API_KEY=.*": f"DOUBAO_API_KEY={values['api_key']}",
            r"DOUBAO_MODEL=.*": f"DOUBAO_MODEL={values['model']}",
            r"MAX_SEARCH_ITERATIONS=.*": f"MAX_SEARCH_ITERATIONS={values['max_iterations']}",
        }
        for pattern, replacement in replacements.items():
            import re
            content = re.sub(pattern, replacement, content)
        path.write_text(content, encoding="utf-8")

    def _show_about(self):
        """关于对话框"""
        QMessageBox.about(
            self, "关于",
            "🔍 企业智能搜索代理 v1.0\n\n"
            "基于 Doubao（豆包）大模型的\n"
            "多源智能搜索桌面应用。\n\n"
            "搜索后端: SQLite | ChromaDB | Whoosh | CodeRepo | EnterpriseSDK\n"
            "推理引擎: Doubao via Volcengine Ark"
        )


# ================================================================
# 设置对话框
# ================================================================

class SettingsDialog(QDialog):
    """API 配置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ API 配置")
        self.setMinimumWidth(450)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.api_key_input = QLineEdit(DOUBAO_API_KEY)
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("ark-xxxxxxxxxxxx")
        form.addRow("API Key:", self.api_key_input)

        self.model_input = QLineEdit(DOUBAO_MODEL)
        self.model_input.setPlaceholderText("doubao-seed-1-8-251228")
        form.addRow("模型名称:", self.model_input)

        self.iterations_input = QLineEdit(str(MAX_SEARCH_ITERATIONS))
        form.addRow("最大搜索轮次:", self.iterations_input)

        layout.addLayout(form)

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self) -> dict:
        return {
            "api_key": self.api_key_input.text().strip(),
            "model": self.model_input.text().strip(),
            "max_iterations": self.iterations_input.text().strip(),
        }
