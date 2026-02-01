"""
提示词管理API路由

提供提示词模板的创建、管理、格式化等功能接口。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from app.models.database import get_db
from app.models.schemas import (
    ApiResponse,
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptTemplateResponse,
    PromptFormatRequest,
    PromptFormatResponse
)
from app.core.prompt_manager import prompt_manager
from app.models.database import PromptTemplate
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/prompt", tags=["提示词管理"])


@router.post("/create", response_model=PromptTemplateResponse)
async def create_prompt_template(
    template: PromptTemplateCreate,
    db: Session = Depends(get_db)
):
    """
    创建提示词模板
    
    创建新的提示词模板，支持变量占位符。
    
    Args:
        template: 提示词模板数据
    
    Returns:
        创建的提示词模板
    
    Examples:
        POST /api/v1/prompt/create
        {
            "name": "my_template",
            "category": "development",
            "system_prompt": "你是一个助手",
            "user_prompt_template": "帮我{task}",
            "variables": ["task"]
        }
    """
    try:
        # 检查模板名称是否已存在
        existing = db.query(PromptTemplate).filter(
            PromptTemplate.name == template.name
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"模板名称已存在: {template.name}"
            )
        
        # 创建模板
        result = prompt_manager.create_template(db, template)
        
        logger.info(f"创建提示词模板成功: {template.name}")
        
        return PromptTemplateResponse.model_validate(result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建提示词模板失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建提示词模板失败: {str(e)}"
        )


@router.get("/list", response_model=list[PromptTemplateResponse])
async def list_prompt_templates(
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    列出提示词模板
    
    支持按分类和状态筛选，支持分页。
    
    Args:
        category: 分类筛选
        is_active: 是否启用筛选
        skip: 跳过的记录数
        limit: 返回的最大记录数
    
    Returns:
        提示词模板列表
    
    Examples:
        GET /api/v1/prompt/list?category=development&is_active=true&skip=0&limit=10
    """
    try:
        templates = prompt_manager.list_templates(
            db,
            category=category,
            is_active=is_active,
            skip=skip,
            limit=limit
        )
        
        return [PromptTemplateResponse.model_validate(t) for t in templates]
        
    except Exception as e:
        logger.error(f"列出提示词模板失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"列出提示词模板失败: {str(e)}"
        )


@router.get("/{template_id}", response_model=PromptTemplateResponse)
async def get_prompt_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """
    获取提示词模板详情
    
    Args:
        template_id: 模板ID
    
    Returns:
        提示词模板详情
    
    Examples:
        GET /api/v1/prompt/1
    """
    try:
        template = prompt_manager.get_template_by_id(db, template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模板不存在: {template_id}"
            )
        
        return PromptTemplateResponse.model_validate(template)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取提示词模板失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取提示词模板失败: {str(e)}"
        )


@router.put("/{template_id}", response_model=PromptTemplateResponse)
async def update_prompt_template(
    template_id: int,
    update_data: PromptTemplateUpdate,
    db: Session = Depends(get_db)
):
    """
    更新提示词模板
    
    Args:
        template_id: 模板ID
        update_data: 更新数据
    
    Returns:
        更新后的提示词模板
    
    Examples:
        PUT /api/v1/prompt/1
        {
            "system_prompt": "更新后的系统提示词"
        }
    """
    try:
        template = prompt_manager.update_template(db, template_id, update_data)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模板不存在: {template_id}"
            )
        
        logger.info(f"更新提示词模板成功: {template_id}")
        
        return PromptTemplateResponse.model_validate(template)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新提示词模板失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新提示词模板失败: {str(e)}"
        )


@router.delete("/{template_id}")
async def delete_prompt_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """
    删除提示词模板
    
    Args:
        template_id: 模板ID
    
    Returns:
        删除结果
    
    Examples:
        DELETE /api/v1/prompt/1
    """
    try:
        success = prompt_manager.delete_template(db, template_id)
        if success:
            return ApiResponse(
                success=True,
                message=f"模板删除成功: {template_id}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模板不存在: {template_id}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除提示词模板失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除提示词模板失败: {str(e)}"
        )


@router.post("/format", response_model=PromptFormatResponse)
async def format_prompt(
    request: PromptFormatRequest,
    db: Session = Depends(get_db)
):
    """
    格式化提示词
    
    使用提供的变量值替换模板中的占位符。
    
    Args:
        request: 格式化请求，包含模板名称和变量值
    
    Returns:
        格式化后的提示词
    
    Examples:
        POST /api/v1/prompt/format
        {
            "template_name": "my_template",
            "variables": {"task": "写一个Python函数"}
        }
    """
    try:
        result = prompt_manager.format_prompt(
            db,
            request.template_name,
            request.variables
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"格式化提示词失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"格式化提示词失败: {str(e)}"
        )


@router.get("/categories/list")
async def list_prompt_categories(db: Session = Depends(get_db)):
    """
    列出所有提示词分类
    
    Returns:
        分类列表
    
    Examples:
        GET /api/v1/prompt/categories/list
    """
    try:
        categories = prompt_manager.get_categories(db)
        return ApiResponse(
            success=True,
            message="获取分类列表成功",
            data=categories
        )
    except Exception as e:
        logger.error(f"获取分类列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取分类列表失败: {str(e)}"
        )


@router.post("/initialize")
async def initialize_default_templates(db: Session = Depends(get_db)):
    """
    初始化默认提示词模板
    
    创建系统预置的HIS开发相关提示词模板。
    如果模板已存在则跳过。
    
    Returns:
        初始化结果
    
    Examples:
        POST /api/v1/prompt/initialize
    """
    try:
        prompt_manager.initialize_default_templates(db)
        
        return ApiResponse(
            success=True,
            message="默认模板初始化完成"
        )
        
    except Exception as e:
        logger.error(f"初始化默认模板失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"初始化默认模板失败: {str(e)}"
        )
