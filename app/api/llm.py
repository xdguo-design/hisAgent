"""
LLM相关API路由

提供LLM对话、模型管理等功能接口。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from app.models.database import get_db
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    ApiResponse,
    ModelConfigCreate,
    ModelConfigUpdate,
    ModelConfigResponse
)
from app.core.llm_service import llm_service
from app.models.database import ModelConfig
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/llm", tags=["LLM管理"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    普通对话接口
    
    发送对话请求并一次性返回完整回复。
    
    Args:
        request: 对话请求，包含消息列表和配置选项
    
    Returns:
        对话响应，包含AI回复内容和元数据
    
    Examples:
        POST /api/v1/llm/chat
        {
            "messages": [
                {"role": "user", "content": "你好"}
            ],
            "model_config_name": "default"
        }
    """
    try:
        # 转换消息格式
        messages = [{"role": msg.role.value, "content": msg.content} for msg in request.messages]
        
        # 调用LLM服务
        result = llm_service.chat_with_config(
            messages=messages,
            config_name=request.model_config_name,
            stream=request.stream
        )
        
        return ChatResponse(
            content=result["content"],
            model=result["model"],
            usage=result["usage"]
        )
        
    except Exception as e:
        logger.error(f"对话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"对话失败: {str(e)}"
        )


@router.get("/models")
async def list_models():
    """
    列出所有可用模型
    
    Returns:
        模型列表，包含模型名称和描述
    
    Examples:
        GET /api/v1/llm/models
    """
    try:
        models = llm_service.list_models()
        return ApiResponse(
            success=True,
            message="获取模型列表成功",
            data=models
        )
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型列表失败: {str(e)}"
        )


@router.post("/config", response_model=ModelConfigResponse)
async def create_model_config(
    config: ModelConfigCreate,
    db: Session = Depends(get_db)
):
    """
    创建模型配置
    
    创建新的模型配置，可以设置temperature、max_tokens等参数。
    
    Args:
        config: 模型配置数据
    
    Returns:
        创建的模型配置
    
    Examples:
        POST /api/v1/llm/config
        {
            "name": "creative",
            "model_name": "glm-4",
            "temperature": 1.2,
            "max_tokens": 3000
        }
    """
    try:
        # 检查配置名是否已存在
        existing = db.query(ModelConfig).filter(ModelConfig.name == config.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"配置名称已存在: {config.name}"
            )
        
        # 如果设置为默认，取消其他默认配置
        if config.is_default:
            db.query(ModelConfig).filter(ModelConfig.is_default == True).update({"is_default": False})
        
        # 创建配置
        model_config = ModelConfig(**config.model_dump())
        db.add(model_config)
        db.commit()
        db.refresh(model_config)
        
        logger.info(f"创建模型配置成功: {config.name}")
        
        return ModelConfigResponse.model_validate(model_config)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"创建模型配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建模型配置失败: {str(e)}"
        )


@router.get("/config", response_model=list[ModelConfigResponse])
async def list_model_configs(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    列出模型配置
    
    支持分页和状态筛选。
    
    Args:
        skip: 跳过的记录数
        limit: 返回的最大记录数
        is_active: 是否启用筛选
    
    Returns:
        模型配置列表
    
    Examples:
        GET /api/v1/llm/config?skip=0&limit=10&is_active=true
    """
    try:
        query = db.query(ModelConfig)
        
        if is_active is not None:
            query = query.filter(ModelConfig.is_active == is_active)
        
        configs = query.offset(skip).limit(limit).all()
        
        return [ModelConfigResponse.model_validate(c) for c in configs]
        
    except Exception as e:
        logger.error(f"列出模型配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"列出模型配置失败: {str(e)}"
        )


@router.get("/config/{config_id}", response_model=ModelConfigResponse)
async def get_model_config(
    config_id: int,
    db: Session = Depends(get_db)
):
    """
    获取模型配置详情
    
    Args:
        config_id: 配置ID
    
    Returns:
        模型配置详情
    
    Examples:
        GET /api/v1/llm/config/1
    """
    try:
        config = db.query(ModelConfig).filter(ModelConfig.id == config_id).first()
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"配置不存在: {config_id}"
            )
        
        return ModelConfigResponse.model_validate(config)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模型配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型配置失败: {str(e)}"
        )


@router.put("/config/{config_id}", response_model=ModelConfigResponse)
async def update_model_config(
    config_id: int,
    update_data: ModelConfigUpdate,
    db: Session = Depends(get_db)
):
    """
    更新模型配置
    
    Args:
        config_id: 配置ID
        update_data: 更新数据
    
    Returns:
        更新后的模型配置
    
    Examples:
        PUT /api/v1/llm/config/1
        {
            "temperature": 0.8,
            "max_tokens": 2500
        }
    """
    try:
        config = db.query(ModelConfig).filter(ModelConfig.id == config_id).first()
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"配置不存在: {config_id}"
            )
        
        # 更新字段
        update_dict = update_data.model_dump(exclude_unset=True)
        
        # 如果设置为默认，取消其他默认配置
        if update_dict.get("is_default") == True:
            db.query(ModelConfig).filter(ModelConfig.id != config_id).filter(ModelConfig.is_default == True).update({"is_default": False})
        
        for key, value in update_dict.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        db.commit()
        db.refresh(config)
        
        logger.info(f"更新模型配置成功: {config_id}")
        
        return ModelConfigResponse.model_validate(config)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新模型配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新模型配置失败: {str(e)}"
        )


@router.delete("/config/{config_id}")
async def delete_model_config(
    config_id: int,
    db: Session = Depends(get_db)
):
    """
    删除模型配置
    
    Args:
        config_id: 配置ID
    
    Returns:
        删除结果
    
    Examples:
        DELETE /api/v1/llm/config/1
    """
    try:
        config = db.query(ModelConfig).filter(ModelConfig.id == config_id).first()
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"配置不存在: {config_id}"
            )
        
        db.delete(config)
        db.commit()
        
        logger.info(f"删除模型配置成功: {config_id}")
        
        return ApiResponse(
            success=True,
            message=f"配置删除成功: {config_id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除模型配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除模型配置失败: {str(e)}"
        )
