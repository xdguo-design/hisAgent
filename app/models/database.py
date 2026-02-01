"""
数据库模块

定义数据库连接、会话管理和所有数据表实体。
使用SQLAlchemy ORM进行数据库操作。
"""

from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from typing import Generator
from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


# 创建数据库引擎
engine = create_engine(
    settings.database_url,
    echo=False,  # 生产环境设为False，开发调试时可设为True查看SQL
    pool_pre_ping=True  # 连接池预检，避免连接失效
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类，所有模型类继承自此
Base = declarative_base()


class ModelConfig(Base):
    """
    模型配置实体
    
    存储LLM模型的配置参数，包括：
    - 模型名称（如glm-4）
    - 生成参数（temperature, max_tokens, top_p等）
    - 配置的描述信息
    - API密钥
    """
    __tablename__ = "model_configs"
    
    # 主键ID
    id = Column(Integer, primary_key=True, index=True, comment="主键ID")
    
    # 配置名称（唯一标识）
    name = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="配置名称"
    )
    
    # 模型名称（如glm-4, glm-4-plus等）
    model_name = Column(String(100), nullable=False, comment="模型名称")
    
    # API密钥
    api_key = Column(String(500), nullable=False, comment="API密钥")
    
    # API基础URL（可选，用于自定义端点）
    api_base = Column(String(500), nullable=True, comment="API基础URL")
    
    # 温度参数：控制输出的随机性，范围0-2
    # 0：确定性输出，2：高度随机
    temperature = Column(Float, default=0.7, comment="温度参数")
    
    # 最大生成的token数量
    max_tokens = Column(Integer, default=2000, comment="最大token数")
    
    # Top-p采样参数：控制核采样的阈值
    top_p = Column(Float, default=0.9, comment="Top-p参数")
    
    # 配置描述
    description = Column(Text, comment="配置描述")
    
    # 是否启用
    is_active = Column(Boolean, default=True, comment="是否启用")
    
    # 是否为默认配置
    is_default = Column(Boolean, default=False, comment="是否为默认配置")
    
    # 创建时间
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    
    # 更新时间
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间"
    )


class PromptTemplate(Base):
    """
    提示词模板实体
    
    存储系统提示词和用户提示词模板，支持变量替换。
    用于构建不同场景下的对话提示。
    """
    __tablename__ = "prompt_templates"
    
    # 主键ID
    id = Column(Integer, primary_key=True, index=True, comment="主键ID")
    
    # 模板名称（唯一标识）
    name = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="模板名称"
    )
    
    # 模板分类（如：code_review, development, qa, workflow等）
    category = Column(String(50), nullable=False, index=True, comment="模板分类")
    
    # 系统提示词：定义AI的角色和行为
    system_prompt = Column(Text, nullable=False, comment="系统提示词")
    
    # 用户提示词模板：包含占位符，可替换为实际内容
    user_prompt_template = Column(Text, nullable=False, comment="用户提示词模板")
    
    # 模板描述
    description = Column(Text, comment="模板描述")
    
    # 模板变量列表（JSON字符串存储）
    # 如：["code_path", "code_content"]
    variables = Column(Text, comment="模板变量列表")
    
    # 是否启用
    is_active = Column(Boolean, default=True, comment="是否启用")
    
    # 创建时间
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    
    # 更新时间
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间"
    )


class KnowledgeBase(Base):
    """
    知识库实体
    
    存储向量知识库的配置信息，包括：
    - 知识库基本信息（名称、路径、描述）
    - 向量化参数（embedding模型、chunk大小等）
    """
    __tablename__ = "knowledge_bases"
    
    # 主键ID
    id = Column(Integer, primary_key=True, index=True, comment="主键ID")
    
    # 知识库名称（唯一标识）
    name = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="知识库名称"
    )
    
    # 知识库数据路径
    path = Column(String(500), nullable=False, comment="知识库数据路径")
    
    # 知识库描述
    description = Column(Text, comment="知识库描述")
    
    # Embedding模型名称（如text-embedding-ada-002）
    embedding_model = Column(
        String(100),
        default="text-embedding-ada-002",
        comment="Embedding模型"
    )
    
    # 文本分块大小（字符数）
    chunk_size = Column(Integer, default=512, comment="分块大小")
    
    # 文本分块重叠大小（字符数）
    chunk_overlap = Column(Integer, default=50, comment="分块重叠大小")
    
    # 文本分块类型（mixed: 混合策略, ast: AST分块, sentence: 句子级, semantic: 语义级, custom: 自定义）
    splitter_type = Column(String(50), default="mixed", comment="分块类型")
    
    # 知识库类型（如：chroma, faiss等）
    store_type = Column(String(50), default="chroma", comment="向量库类型")
    
    # 文档数量
    document_count = Column(Integer, default=0, comment="文档数量")
    
    # 是否启用
    is_active = Column(Boolean, default=True, comment="是否启用")
    
    # 创建时间
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    
    # 更新时间
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间"
    )


class Conversation(Base):
    """
    对话记录实体
    
    存储与AI的对话历史，用于上下文保持和调试。
    """
    __tablename__ = "conversations"
    
    # 主键ID
    id = Column(Integer, primary_key=True, index=True, comment="主键ID")
    
    # 会话ID（UUID）
    session_id = Column(String(100), nullable=False, index=True, comment="会话ID")
    
    # 消息类型：system, user, assistant
    role = Column(String(20), nullable=False, comment="角色类型")
    
    # 消息内容
    content = Column(Text, nullable=False, comment="消息内容")
    
    # 使用的模型配置ID
    model_config_id = Column(
        Integer,
        ForeignKey("model_configs.id"),
        comment="模型配置ID"
    )
    
    # 使用的提示词模板ID
    prompt_template_id = Column(
        Integer,
        ForeignKey("prompt_templates.id"),
        comment="提示词模板ID"
    )
    
    # 使用的知识库ID（如果有）
    knowledge_base_id = Column(
        Integer,
        ForeignKey("knowledge_bases.id"),
        comment="知识库ID"
    )
    
    # Token使用情况（JSON格式）
    token_usage = Column(Text, comment="Token使用情况")
    
    # 创建时间
    created_at = Column(DateTime, default=datetime.utcnow, index=True, comment="创建时间")


class Task(Base):
    """
    任务实体
    
    记录异步任务的状态，如知识库索引创建、向量计算等耗时操作。
    """
    __tablename__ = "tasks"
    
    # 主键ID
    id = Column(Integer, primary_key=True, index=True, comment="主键ID")
    
    # 任务类型：create_index, delete_index, rebuild_index等
    task_type = Column(String(50), nullable=False, comment="任务类型")
    
    # 任务状态：pending, running, completed, failed
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="任务状态"
    )
    
    # 任务参数（JSON格式）
    parameters = Column(Text, comment="任务参数")
    
    # 任务结果（JSON格式）
    result = Column(Text, comment="任务结果")
    
    # 错误信息
    error_message = Column(Text, comment="错误信息")
    
    # 进度（0-100）
    progress = Column(Integer, default=0, comment="任务进度")
    
    # 创建时间
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    
    # 开始时间
    started_at = Column(DateTime, comment="开始时间")
    
    # 完成时间
    completed_at = Column(DateTime, comment="完成时间")


def init_db():
    """
    初始化数据库
    
    创建所有数据表。如果表已存在则不会重复创建。
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("数据库初始化成功")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


def get_db() -> Generator:
    """
    获取数据库会话
    
    用于FastAPI的依赖注入，每次请求获取一个新的会话，
    请求结束后自动关闭会话。
    
    Yields:
        数据库会话实例
    
    Examples:
        >>> @app.get("/items")
        >>> def read_items(db: Session = Depends(get_db)):
        >>>     items = db.query(Item).all()
        >>>     return items
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def drop_all_tables():
    """
    删除所有数据表
    
    警告：此操作会删除所有数据，不可逆！
    仅在开发测试时使用。
    """
    try:
        Base.metadata.drop_all(bind=engine)
        logger.warning("所有数据表已删除")
    except Exception as e:
        logger.error(f"删除数据表失败: {e}")
        raise
