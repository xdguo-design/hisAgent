"""
应用配置模块

本模块负责加载和管理应用程序的所有配置项，包括：
- 数据库连接配置
- AI模型API密钥配置
- 日志配置
- 向量数据库配置

配置通过环境变量加载，使用pydantic-settings进行验证和类型转换。
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os


class Settings(BaseSettings):
    """
    应用设置类
    
    使用pydantic进行配置验证，所有配置项都从环境变量中读取。
    如果环境变量未设置，则使用默认值。
    """
    
    # ========== 智谱AI配置 ==========
    zhipuai_api_key: str  # 智谱AI的API密钥，必填
    
    # ========== OpenAI配置（用于Embedding） ==========
    openai_api_key: Optional[str] = None  # OpenAI API密钥，用于文本嵌入（可选）
    
    # ========== 数据库配置 ==========
    database_url: str = "sqlite:///./his_agent.db"  # 数据库连接URL
    
    # ========== 向量数据库配置 ==========
    chroma_persist_dir: str = "./chroma_db"  # ChromaDB持久化存储目录
    
    # ========== 日志配置 ==========
    log_level: str = "INFO"  # 日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_file: str = "logs/his_agent.log"  # 日志文件路径
    
    # ========== API配置 ==========
    api_host: str = "0.0.0.0"  # API服务监听主机
    api_port: int = 8000  # API服务监听端口
    api_prefix: str = "/api/v1"  # API路由前缀
    
    # ========== LLM默认参数配置 ==========
    default_temperature: float = 0.4  # 默认温度参数，控制输出随机性
    default_max_tokens: int = 2000  # 默认最大token数
    default_top_p: float = 0.9  # 默认top_p参数，控制核采样
    
    # ========== 知识库配置 ==========
    default_chunk_size: int = 512  # 默认文本分块大小
    default_chunk_overlap: int = 50  # 默认文本分块重叠大小
    default_top_k: int = 5  # 默认检索结果数量
    default_retrieval_type: str = "hybrid"  # 默认检索类型：hnsw, hybrid
    
    # ========== 文件上传配置 ==========
    max_upload_size: int = 10 * 1024 * 1024  # 最大文件上传大小（10MB）
    allowed_extensions: list = [".txt", ".md", ".pdf", ".doc", ".docx"]  # 允许的文件扩展名
    
    # ========== 安全配置 ==========
    secret_key: str = "your-secret-key-change-this-in-production"  # JWT密钥，生产环境必须修改
    admin_password: str = "admin123"  # 管理员密码，用于配置修改
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    def __init__(self, **kwargs):
        """
        初始化配置
        
        创建必要的目录结构，确保日志目录和向量数据库目录存在。
        """
        super().__init__(**kwargs)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """
        确保必要的目录存在
        
        创建日志目录和向量数据库目录，如果不存在的话。
        """
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        os.makedirs(self.chroma_persist_dir, exist_ok=True)


# 全局配置实例，应用启动时初始化
settings = Settings()
