"""
============================================================
本地日志系统 - 结构化日志，支持同时输出到文件和终端
Local Logging System with Structured Format
============================================================
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

from config import LOG_LEVEL, LOG_FILE, LOG_MAX_BYTES, LOG_BACKUP_COUNT

# 自定义格式化器 - 带颜色的终端输出 + 详细文件输出
class ColoredFormatter(logging.Formatter):
    """终端彩色日志格式化器"""

    COLORS = {
        "DEBUG": "\033[36m",      # 青色
        "INFO": "\033[32m",       # 绿色
        "WARNING": "\033[33m",    # 黄色
        "ERROR": "\033[31m",      # 红色
        "CRITICAL": "\033[35m",   # 紫色
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname_colored = f"{color}{self.BOLD}{record.levelname:<8}{self.RESET}"
        return super().format(record)


class DetailFormatter(logging.Formatter):
    """文件日志详细格式化器"""
    pass


def setup_logger(name: str = "AgenticSearch") -> logging.Logger:
    """
    初始化日志系统，返回配置好的 logger 实例。

    Returns:
        logging.Logger: 配置完成的 logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    # ---- 终端 Handler（彩色） ----
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_fmt = ColoredFormatter(
        "%(asctime)s | %(levelname_colored)s | %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    # ---- 文件 Handler（详细，带轮转） ----
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        str(LOG_FILE),
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_fmt = DetailFormatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    return logger


# 全局 logger 实例
log = setup_logger()
