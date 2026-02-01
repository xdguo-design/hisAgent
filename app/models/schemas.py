"""
API模型模块

定义Pydantic模型，用于API请求和响应的数据验证和序列化。
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
import json


# ========== 模型配置相关模型 ==========

class ModelConfigBase(BaseModel):
    """模型配置基础模型"""
    name: str = Field(..., description="配置名称", min_length=1, max_length=100)
    model_name: str = Field(..., description="模型名称", min_length=1, max_length=100)
    api_key: str = Field(..., description="API密钥", min_length=1, max_length=500)
    api_base: Optional[str] = Field(None, description="API基础URL", max_length=500)
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度参数(0-2)")
    max_tokens: int = Field(default=2000, ge=1, le=32000, description="最大token数")
    top_p: float = Field(default=0.9, ge=0, le=1, description="Top-p参数(0-1)")
    description: Optional[str] = Field(None, description="配置描述")
    is_active: bool = Field(default=True, description="是否启用")
    is_default: bool = Field(default=False, description="是否为默认配置")


class ModelConfigCreate(ModelConfigBase):
    """创建模型配置请求模型"""
    pass


class ModelConfigUpdate(BaseModel):
    """更新模型配置请求模型（所有字段可选）"""
    model_name: Optional[str] = Field(None, min_length=1, max_length=100)
    api_key: Optional[str] = Field(None, min_length=1, max_length=500)
    api_base: Optional[str] = Field(None, max_length=500)
    temperature: Optional[float] = Field(None, ge=0, le=2)
    max_tokens: Optional[int] = Field(None, ge=1, le=32000)
    top_p: Optional[float] = Field(None, ge=0, le=1)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class ModelConfigResponse(ModelConfigBase):
    """模型配置响应模型"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ========== 提示词模板相关模型 ==========

class PromptTemplateBase(BaseModel):
    """提示词模板基础模型"""
    name: str = Field(..., description="模板名称", min_length=1, max_length=100)
    category: str = Field(..., description="模板分类", min_length=1, max_length=50)
    system_prompt: str = Field(..., description="系统提示词", min_length=1)
    user_prompt_template: str = Field(..., description="用户提示词模板", min_length=1)
    description: Optional[str] = Field(None, description="模板描述")
    variables: Optional[List[str]] = Field(default_factory=list, description="模板变量列表")
    is_active: bool = Field(default=True, description="是否启用")


class PromptTemplateCreate(PromptTemplateBase):
    """创建提示词模板请求模型"""
    pass


class PromptTemplateUpdate(BaseModel):
    """更新提示词模板请求模型（所有字段可选）"""
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    system_prompt: Optional[str] = Field(None, min_length=1)
    user_prompt_template: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    variables: Optional[List[str]] = None
    is_active: Optional[bool] = None


class PromptTemplateResponse(PromptTemplateBase):
    """提示词模板响应模型"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_validator('variables', mode='before')
    @classmethod
    def parse_variables(cls, v: Union[str, List[str], None]) -> Optional[List[str]]:
        """解析变量字段，支持字符串（JSON）和列表两种格式"""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return []
        return v if isinstance(v, list) else []


class PromptFormatRequest(BaseModel):
    """提示词格式化请求模型"""
    template_name: str = Field(..., description="模板名称")
    variables: Dict[str, str] = Field(..., description="变量值字典")


class PromptFormatResponse(BaseModel):
    """提示词格式化响应模型"""
    system: str = Field(..., description="格式化后的系统提示词")
    user: str = Field(..., description="格式化后的用户提示词")


# ========== 知识库相关模型 ==========

class KnowledgeBaseBase(BaseModel):
    """知识库基础模型"""
    name: str = Field(..., description="知识库名称", min_length=1, max_length=100)
    path: str = Field(..., description="知识库数据路径", min_length=1)
    description: Optional[str] = Field(None, description="知识库描述")
    embedding_model: str = Field(default="text-embedding-ada-002", description="Embedding模型")
    chunk_size: int = Field(default=512, ge=1, description="分块大小")
    chunk_overlap: int = Field(default=50, ge=0, description="分块重叠大小")
    splitter_type: str = Field(default="sentence", description="分块类型")
    store_type: str = Field(default="chroma", description="向量库类型")
    is_active: bool = Field(default=True, description="是否启用")


class KnowledgeBaseCreate(KnowledgeBaseBase):
    """创建知识库请求模型"""
    pass


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库请求模型（所有字段可选）"""
    path: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    embedding_model: Optional[str] = None
    chunk_size: Optional[int] = Field(None, ge=1)
    chunk_overlap: Optional[int] = Field(None, ge=0)
    splitter_type: Optional[str] = None
    store_type: Optional[str] = None
    is_active: Optional[bool] = None


class KnowledgeBaseResponse(KnowledgeBaseBase):
    """知识库响应模型"""
    id: int
    document_count: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class KnowledgeBaseCreateIndexRequest(BaseModel):
    """创建知识库索引请求模型"""
    data_path: str = Field(..., description="数据路径")
    chunk_size: Optional[int] = Field(None, ge=1)
    chunk_overlap: Optional[int] = Field(None, ge=0)
    embedding_model: Optional[str] = None
    splitter_type: Optional[str] = Field(default="sentence", description="分块类型")


class KnowledgeBaseQueryRequest(BaseModel):
    """知识库查询请求模型"""
    query: str = Field(..., description="查询内容", min_length=1)
    top_k: int = Field(default=5, ge=1, le=20, description="返回结果数量")
    similarity_threshold: float = Field(default=0.7, ge=0, le=1, description="相似度阈值")


class KnowledgeBaseQueryResponse(BaseModel):
    """知识库查询响应模型"""
    answer: str = Field(..., description="回答内容")
    sources: List[str] = Field(default_factory=list, description="来源文件列表")
    similarity_scores: Optional[List[float]] = Field(default_factory=list, description="相似度分数列表")


class DocumentUploadResponse(BaseModel):
    """文档上传响应模型"""
    filename: str = Field(..., description="文件名")
    size: int = Field(..., description="文件大小(字节)")
    path: str = Field(..., description="存储路径")
    status: str = Field(..., description="处理状态")


class CreateIndexFromFilesRequest(BaseModel):
    """从文件创建索引请求模型"""
    name: str = Field(..., description="知识库名称", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="知识库描述")
    chunk_size: int = Field(default=512, ge=1, description="分块大小")
    chunk_overlap: int = Field(default=50, ge=0, description="分块重叠大小")
    embedding_model: str = Field(default="zhipuai-embedding", description="Embedding模型")
    splitter_type: str = Field(default="sentence", description="分块类型")


class AddDocumentsRequest(BaseModel):
    """向知识库添加文档请求模型"""
    name: str = Field(..., description="知识库名称", min_length=1, max_length=100)
    chunk_size: int = Field(default=512, ge=1, description="分块大小")
    chunk_overlap: int = Field(default=50, ge=0, description="分块重叠大小")
    embedding_model: Optional[str] = Field(None, description="Embedding模型（不指定则使用知识库原有模型）")


class DocumentInfo(BaseModel):
    """文档信息模型"""
    doc_id: str = Field(..., description="文档ID")
    file_name: str = Field(..., description="文件名")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class DeleteDocumentsRequest(BaseModel):
    """删除知识库文档请求模型"""
    name: str = Field(..., description="知识库名称", min_length=1, max_length=100)
    file_names: List[str] = Field(..., description="要删除的文件名列表", min_length=1)


class DeleteDocumentsResponse(BaseModel):
    """删除文档响应模型"""
    success: bool = Field(..., description="是否成功")
    deleted_count: int = Field(..., description="删除的文档数量")
    message: str = Field(..., description="响应消息")


# ========== 对话相关模型 ==========

class MessageRole(str, Enum):
    """消息角色枚举"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Message(BaseModel):
    """消息模型"""
    role: MessageRole = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容", min_length=1)


class ChatRequest(BaseModel):
    """聊天请求模型"""
    messages: List[Message] = Field(..., description="消息列表", min_length=1)
    model_config_name: Optional[str] = Field(None, description="模型配置名称")
    prompt_template_name: Optional[str] = Field(None, description="提示词模板名称")
    knowledge_base_name: Optional[str] = Field(None, description="知识库名称")
    stream: bool = Field(default=False, description="是否流式输出")


class ChatResponse(BaseModel):
    """聊天响应模型"""
    content: str = Field(..., description="AI回复内容")
    model: str = Field(..., description="使用的模型")
    usage: Dict[str, int] = Field(default_factory=dict, description="Token使用情况")


class ConversationResponse(BaseModel):
    """对话记录响应模型"""
    id: int
    session_id: str
    role: MessageRole
    content: str
    model_config_id: Optional[int] = None
    prompt_template_id: Optional[int] = None
    knowledge_base_id: Optional[int] = None
    token_usage: Optional[Dict[str, int]] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ========== 任务相关模型 ==========

class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskType(str, Enum):
    """任务类型枚举"""
    CREATE_INDEX = "create_index"
    DELETE_INDEX = "delete_index"
    REBUILD_INDEX = "rebuild_index"
    ADD_DOCUMENTS = "add_documents"


class TaskBase(BaseModel):
    """任务基础模型"""
    task_type: TaskType = Field(..., description="任务类型")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="任务参数")
    result: Optional[Dict[str, Any]] = Field(None, description="任务结果")
    error_message: Optional[str] = Field(None, description="错误信息")
    progress: int = Field(default=0, ge=0, le=100, description="任务进度")


class TaskResponse(TaskBase):
    """任务响应模型"""
    id: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# ========== 通用响应模型 ==========

class ApiResponse(BaseModel):
    """通用API响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[Any] = Field(None, description="响应数据")


class PaginatedResponse(BaseModel):
    """分页响应模型"""
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页记录数")
    items: List[Any] = Field(default_factory=list, description="数据列表")


# ========== HIS业务相关模型 ==========

class HISCodeReviewRequest(BaseModel):
    """HIS代码审查请求模型"""
    code_path: str = Field(..., description="代码文件路径")
    code_content: str = Field(..., description="代码内容", min_length=1)
    review_aspects: Optional[List[str]] = Field(
        default_factory=lambda: ["quality", "business", "security", "performance", "compliance"],
        description="审查方面"
    )


class HISDevelopmentAssistantRequest(BaseModel):
    """HIS开发助手请求模型"""
    requirement: str = Field(..., description="需求描述", min_length=1)
    context: str = Field(default="", description="背景信息")
    department: Optional[str] = Field(None, description="所属科室")
    module: Optional[str] = Field(None, description="所属模块")


class HISWorkflowDesignRequest(BaseModel):
    """HIS临床流程设计请求模型"""
    workflow_requirement: str = Field(..., description="流程设计需求", min_length=1)
    department: str = Field(..., description="科室名称", min_length=1)
    workflow_type: Optional[str] = Field(None, description="流程类型")


class HISKnowledgeQARequest(BaseModel):
    """HIS知识问答请求模型"""
    question: str = Field(..., description="问题内容", min_length=1)
    use_knowledge_base: bool = Field(default=False, description="是否使用知识库")
    knowledge_base_name: Optional[str] = Field(None, description="知识库名称")
