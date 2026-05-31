"""
PC 桌面应用入口
Desktop Application Entry Point

运行方式:
    python -m pc_app.main
    或
    cd agentic_search && python pc_app/main.py
"""
import sys
import os
from pathlib import Path

# 确保项目根目录在 path 中
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from pc_app.main_window import MainWindow, STYLE_DARK


def main():
    # 高 DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("企业智能搜索代理")
    app.setOrganizationName("EnterpriseSearch")
    app.setStyle("Fusion")  # 跨平台一致外观
    app.setStyleSheet(STYLE_DARK)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
