"""
辅助函数模块

提供各种通用的辅助函数，包括文件处理、字符串处理、数据验证等。
"""

import os
import re
import json
from typing import List, Optional, Any, Dict
from datetime import datetime


def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
    """
    验证文件扩展名是否在允许的列表中
    
    Args:
        filename: 文件名
        allowed_extensions: 允许的扩展名列表，如 [".txt", ".md", ".pdf"]
    
    Returns:
        如果扩展名合法返回True，否则返回False
    
    Examples:
        >>> validate_file_extension("document.txt", [".txt", ".md"])
        True
        >>> validate_file_extension("document.pdf", [".txt", ".md"])
        False
    """
    # 获取文件扩展名（小写）
    ext = os.path.splitext(filename)[1].lower()
    return ext in allowed_extensions


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除不安全字符
    
    Args:
        filename: 原始文件名
    
    Returns:
        清理后的安全文件名
    
    Examples:
        >>> sanitize_filename("my/file*.txt")
        'my_file.txt'
    """
    # 移除路径分隔符
    filename = os.path.basename(filename)
    # 替换不安全字符为下划线
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # 移除连续的下划线
    filename = re.sub(r'_+', '_', filename)
    # 移除首尾的下划线和点
    filename = filename.strip('._')
    return filename or "unnamed"


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """
    截断过长的文本
    
    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后添加的后缀
    
    Returns:
        截断后的文本
    
    Examples:
        >>> truncate_text("这是一段很长的文本...", 10)
        '这是一段很...'
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def safe_json_loads(text: str, default: Any = None) -> Any:
    """
    安全地解析JSON字符串，失败时返回默认值
    
    Args:
        text: JSON字符串
        default: 解析失败时的默认返回值
    
    Returns:
        解析后的对象或默认值
    
    Examples:
        >>> safe_json_loads('{"key": "value"}')
        {'key': 'value'}
        >>> safe_json_loads('invalid json', {})
        {}
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def format_datetime(dt: Optional[datetime], fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化日期时间
    
    Args:
        dt: 日期时间对象，如果为None则返回当前时间
        fmt: 格式化字符串
    
    Returns:
        格式化后的日期时间字符串
    
    Examples:
        >>> format_datetime(datetime(2024, 1, 1, 12, 0))
        '2024-01-01 12:00:00'
    """
    if dt is None:
        dt = datetime.utcnow()
    return dt.strftime(fmt)


def extract_variables_from_template(template: str) -> List[str]:
    """
    从模板字符串中提取变量名（格式为{variable}）
    
    Args:
        template: 包含变量的模板字符串
    
    Returns:
        变量名列表
    
    Examples:
        >>> extract_variables_from_template("Hello {name}, your age is {age}")
        ['name', 'age']
    """
    pattern = r'\{([^{}]+)\}'
    return re.findall(pattern, template)


def merge_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并多个字典，后面的字典会覆盖前面的同名键
    
    Args:
        *dicts: 要合并的字典
    
    Returns:
        合并后的字典
    
    Examples:
        >>> merge_dicts({"a": 1}, {"b": 2}, {"a": 3})
        {'a': 3, 'b': 2}
    """
    result = {}
    for d in dicts:
        result.update(d)
    return result


def ensure_directory_exists(path: str) -> bool:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        path: 目录路径
    
    Returns:
        True如果目录存在或创建成功，False如果失败
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except OSError:
        return False


def get_file_size(path: str) -> Optional[int]:
    """
    获取文件大小（字节）
    
    Args:
        path: 文件路径
    
    Returns:
        文件大小（字节），如果文件不存在或无法访问则返回None
    """
    try:
        return os.path.getsize(path)
    except OSError:
        return None


def is_valid_url(url: str) -> bool:
    """
    验证URL格式是否有效
    
    Args:
        url: 要验证的URL
    
    Returns:
        True如果URL格式有效，否则返回False
    
    Examples:
        >>> is_valid_url("https://example.com")
        True
        >>> is_valid_url("not a url")
        False
    """
    pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return pattern.match(url) is not None
