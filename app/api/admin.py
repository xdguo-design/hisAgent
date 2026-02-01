"""
管理员配置API路由

提供管理员配置修改接口，需要密码验证。
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional
from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/admin", tags=["管理员配置"])


class AdminConfigRequest(BaseModel):
    password: str
    default_chunk_size: Optional[int] = None
    default_chunk_overlap: Optional[int] = None
    default_top_k: Optional[int] = None
    default_retrieval_type: Optional[str] = None


class AdminConfigResponse(BaseModel):
    default_chunk_size: int
    default_chunk_overlap: int
    default_top_k: int
    default_retrieval_type: str


@router.get("/config", response_model=AdminConfigResponse)
async def get_admin_config():
    """
    获取管理员配置
    
    返回当前的知识库配置参数。
    
    Returns:
        配置响应，包含chunk_size、chunk_overlap和top_k
    
    Examples:
        GET /api/v1/admin/config
        {
            "default_chunk_size": 512,
            "default_chunk_overlap": 50,
            "default_top_k": 5
        }
    """
    try:
        return AdminConfigResponse(
            default_chunk_size=settings.default_chunk_size,
            default_chunk_overlap=settings.default_chunk_overlap,
            default_top_k=settings.default_top_k,
            default_retrieval_type=settings.default_retrieval_type
        )
    except Exception as e:
        logger.error(f"获取管理员配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取配置失败: {str(e)}"
        )


@router.post("/config")
async def update_admin_config(request: AdminConfigRequest):
    """
    更新管理员配置
    
    需要提供管理员密码才能修改配置。
    更新后需要重启服务才能生效。
    
    Args:
        request: 配置更新请求，包含密码和要修改的参数
    
    Returns:
        更新结果
    
    Examples:
        POST /api/v1/admin/config
        {
            "password": "admin123",
            "default_chunk_size": 800,
            "default_chunk_overlap": 200,
            "default_top_k": 10
        }
    """
    try:
        admin_password = getattr(settings, 'admin_password', 'admin123')
        
        if request.password != admin_password:
            logger.warning("管理员密码验证失败")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="管理员密码错误"
            )
        
        updated_fields = []
        
        if request.default_chunk_size is not None:
            if request.default_chunk_size < 100 or request.default_chunk_size > 4096:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="chunk_size必须在100-4096之间"
                )
            settings.default_chunk_size = request.default_chunk_size
            updated_fields.append("default_chunk_size")
        
        if request.default_chunk_overlap is not None:
            if request.default_chunk_overlap < 0 or request.default_chunk_overlap > 1000:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="chunk_overlap必须在0-1000之间"
                )
            settings.default_chunk_overlap = request.default_chunk_overlap
            updated_fields.append("default_chunk_overlap")
        
        if request.default_top_k is not None:
            if request.default_top_k < 1 or request.default_top_k > 100:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="top_k必须在1-100之间"
                )
            settings.default_top_k = request.default_top_k
            updated_fields.append("default_top_k")
        
        if request.default_retrieval_type is not None:
            if request.default_retrieval_type not in ["hnsw", "hybrid"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="retrieval_type必须是hnsw或hybrid"
                )
            settings.default_retrieval_type = request.default_retrieval_type
            updated_fields.append("default_retrieval_type")
        
        if not updated_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未提供任何需要更新的参数"
            )
        
        logger.info(f"管理员配置更新成功: {', '.join(updated_fields)}")
        
        return {
            "success": True,
            "message": "配置更新成功，重启服务后生效",
            "updated_fields": updated_fields,
            "current_config": {
                "default_chunk_size": settings.default_chunk_size,
                "default_chunk_overlap": settings.default_chunk_overlap,
                "default_top_k": settings.default_top_k,
                "default_retrieval_type": settings.default_retrieval_type
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新管理员配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新配置失败: {str(e)}"
        )
