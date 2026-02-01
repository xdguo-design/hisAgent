"""
日志工具模块

提供统一的日志记录功能，支持控制台和文件输出。
使用Python标准库logging实现。
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional
from app.config import settings


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: str = None
) -> logging.Logger:
    """
    配置并返回一个logger实例
    
    Args:
        name: logger名称，通常使用模块名
        log_file: 日志文件路径，如果为None则只输出到控制台
        level: 日志级别，如果为None则使用配置文件中的设置
    
    Returns:
        配置好的logger实例
    
    Examples:
        >>> logger = setup_logger(__name__)
        >>> logger.info("这是一条信息")
    """
    # 创建logger实例
    logger = logging.getLogger(name)
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 设置日志级别
    log_level = getattr(logging, (level or settings.log_level).upper())
    logger.setLevel(log_level)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 添加控制台handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 添加文件handler（如果指定了日志文件）
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # 使用RotatingFileHandler，单个文件最大10MB，保留5个备份
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# 默认logger实例，用于应用级日志
app_logger = setup_logger("his_agent", settings.log_file)
