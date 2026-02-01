"""
HIS业务API路由

提供HIS系统开发相关的专业功能接口，包括代码审查、开发助手、知识问答等。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from app.models.database import get_db
from app.models.schemas import (
    ApiResponse,
    ChatResponse,
    HISCodeReviewRequest,
    HISDevelopmentAssistantRequest,
    HISWorkflowDesignRequest,
    HISKnowledgeQARequest
)
from app.core.his_expert import his_expert
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/his", tags=["HIS业务"])


@router.post("/code-review", response_model=ChatResponse)
async def his_code_review(
    request: HISCodeReviewRequest,
    model_config_name: Optional[str] = None
):
    """
    HIS代码审查
    
    对HIS系统代码进行专业审查，包括代码质量、业务逻辑、安全性等方面。
    
    Args:
        request: 代码审查请求，包含代码路径和内容
        model_config_name: 使用的模型配置名称（可选）
    
    Returns:
        审查结果
    
    Examples:
        POST /api/v1/his/code-review
        {
            "code_path": "src/medical/OrderService.java",
            "code_content": "public class OrderService { ... }",
            "review_aspects": ["quality", "business", "security"]
        }
    """
    try:
        result = his_expert.code_review(request, model_config_name)
        return result
    except Exception as e:
        logger.error(f"HIS代码审查失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"HIS代码审查失败: {str(e)}"
        )


@router.post("/development-assistant", response_model=ChatResponse)
async def his_development_assistant(
    request: HISDevelopmentAssistantRequest,
    model_config_name: Optional[str] = None
):
    """
    HIS开发助手
    
    为HIS系统开发提供专业的技术咨询和方案设计。
    
    Args:
        request: 开发助手请求，包含需求和背景信息
        model_config_name: 使用的模型配置名称（可选）
    
    Returns:
        开发方案
    
    Examples:
        POST /api/v1/his/development-assistant
        {
            "requirement": "实现门诊挂号功能",
            "context": "需要支持医保结算",
            "department": "门诊部"
        }
    """
    try:
        result = his_expert.development_assistant(request, model_config_name)
        return result
    except Exception as e:
        logger.error(f"HIS开发助手失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"HIS开发助手失败: {str(e)}"
        )


@router.post("/knowledge-qa", response_model=ChatResponse)
async def his_knowledge_qa(
    request: HISKnowledgeQARequest,
    model_config_name: Optional[str] = None
):
    """
    HIS知识问答
    
    回答HIS系统相关的专业问题，可结合知识库进行回答。
    
    Args:
        request: 知识问答请求，包含问题和是否使用知识库的配置
        model_config_name: 使用的模型配置名称（可选）
    
    Returns:
        问答结果
    
    Examples:
        POST /api/v1/his/knowledge-qa
        {
            "question": "什么是HL7标准？",
            "use_knowledge_base": true,
            "knowledge_base_name": "his_knowledge"
        }
    """
    try:
        result = his_expert.knowledge_qa(request, model_config_name)
        return result
    except Exception as e:
        logger.error(f"HIS知识问答失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"HIS知识问答失败: {str(e)}"
        )


@router.post("/workflow-design", response_model=ChatResponse)
async def his_workflow_design(
    request: HISWorkflowDesignRequest,
    model_config_name: Optional[str] = None
):
    """
    HIS临床流程设计
    
    为医院临床业务流程设计提供专业咨询。
    
    Args:
        request: 流程设计请求，包含需求和科室信息
        model_config_name: 使用的模型配置名称（可选）
    
    Returns:
        流程设计方案
    
    Examples:
        POST /api/v1/his/workflow-design
        {
            "workflow_requirement": "门诊处方流程",
            "department": "药房",
            "workflow_type": "prescription"
        }
    """
    try:
        result = his_expert.workflow_design(request, model_config_name)
        return result
    except Exception as e:
        logger.error(f"HIS流程设计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"HIS流程设计失败: {str(e)}"
        )


@router.post("/database-design", response_model=ChatResponse)
async def his_database_design(
    db_requirement: str,
    business_context: str,
    model_config_name: Optional[str] = None
):
    """
    HIS数据库设计
    
    为HIS系统数据库设计提供专业咨询。
    
    Args:
        db_requirement: 数据库设计需求
        business_context: 业务场景描述
        model_config_name: 使用的模型配置名称（可选）
    
    Returns:
        数据库设计方案
    
    Examples:
        POST /api/v1/his/database-design?db_requirement=设计门诊挂号表&business_context=支持医保结算
    """
    try:
        result = his_expert.database_design(
            db_requirement,
            business_context,
            model_config_name
        )
        return result
    except Exception as e:
        logger.error(f"HIS数据库设计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"HIS数据库设计失败: {str(e)}"
        )


@router.post("/api-design", response_model=ChatResponse)
async def his_api_design(
    api_requirement: str,
    business_context: str,
    model_config_name: Optional[str] = None
):
    """
    HIS API设计
    
    为HIS系统API设计提供专业咨询。
    
    Args:
        api_requirement: API设计需求
        business_context: 业务场景描述
        model_config_name: 使用的模型配置名称（可选）
    
    Returns:
        API设计方案
    
    Examples:
        POST /api/v1/his/api-design?api_requirement=设计挂号接口&business_context=支持医保结算
    """
    try:
        result = his_expert.api_design(
            api_requirement,
            business_context,
            model_config_name
        )
        return result
    except Exception as e:
        logger.error(f"HIS API设计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"HIS API设计失败: {str(e)}"
        )


@router.get("/categories")
async def get_his_categories():
    """
    获取HIS业务分类
    
    Returns:
        业务分类列表
    
    Examples:
        GET /api/v1/his/categories
    """
    try:
        categories = his_expert.get_his_categories()
        return ApiResponse(
            success=True,
            message="获取业务分类成功",
            data=categories
        )
    except Exception as e:
        logger.error(f"获取业务分类失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取业务分类失败: {str(e)}"
        )


@router.get("/departments")
async def get_departments():
    """
    获取医院科室分类
    
    Returns:
        科室分类字典
    
    Examples:
        GET /api/v1/his/departments
    """
    try:
        departments = his_expert.get_departments()
        return ApiResponse(
            success=True,
            message="获取科室分类成功",
            data=departments
        )
    except Exception as e:
        logger.error(f"获取科室分类失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取科室分类失败: {str(e)}"
        )


@router.get("/modules")
async def get_his_modules():
    """
    获取HIS系统模块列表
    
    Returns:
        系统模块列表
    
    Examples:
        GET /api/v1/his/modules
    """
    try:
        modules = his_expert.get_his_modules()
        return ApiResponse(
            success=True,
            message="获取系统模块成功",
            data=modules
        )
    except Exception as e:
        logger.error(f"获取系统模块失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取系统模块失败: {str(e)}"
        )


@router.get("/standards")
async def get_his_standards():
    """
    获取HIS相关标准和规范
    
    Returns:
        标准和规范列表
    
    Examples:
        GET /api/v1/his/standards
    """
    try:
        standards = his_expert.get_his_standards()
        return ApiResponse(
            success=True,
            message="获取标准和规范成功",
            data=standards
        )
    except Exception as e:
        logger.error(f"获取标准和规范失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取标准和规范失败: {str(e)}"
        )
