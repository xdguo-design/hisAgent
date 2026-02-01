"""
文档代码生成API路由

提供文档上传和代码生成的接口。
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
import os
import shutil
import uuid

from app.models.database import get_db
from app.models.schemas import ApiResponse
from app.core.document_generator import document_generator
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/document", tags=["文档代码生成"])


@router.post("/generate", response_model=ApiResponse)
async def generate_code_from_document(
    file: UploadFile = File(...),
    config_name: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    上传文档并生成代码

    上传设计文档（支持md、word格式），解析文档内容并生成Java代码实现。

    Args:
        file: 上传的文档文件
        config_name: 使用的模型配置名称（可选）

    Returns:
        生成的代码结果

    Examples:
        POST /api/v1/document/generate
        Content-Type: multipart/form-data

        file: design.md
        config_name: zhipuai_glm4
    """
    try:
        # 检查文件扩展名
        allowed_extensions = {'.md', '.docx', '.doc'}
        file_ext = os.path.splitext(file.filename)[1].lower()

        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件类型: {file_ext}。支持的类型: {', '.join(allowed_extensions)}"
            )

        # 创建临时上传目录
        upload_dir = os.path.join(os.getcwd(), "temp_uploads")
        os.makedirs(upload_dir, exist_ok=True)

        # 生成唯一文件名
        file_id = str(uuid.uuid4())
        filename = f"{file_id}{file_ext}"
        file_path = os.path.join(upload_dir, filename)

        # 保存文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = os.path.getsize(file_path)
        logger.info(f"文档上传成功: {file.filename} -> {filename} ({file_size} bytes)")

        # 处理文档并生成代码
        result = document_generator.process_document(file_path, config_name)

        # 清理临时文件
        try:
            os.remove(file_path)
        except Exception as e:
            logger.warning(f"清理临时文件失败: {file_path}, {e}")

        if result["success"]:
            return ApiResponse(
                success=True,
                message=f"文档处理成功，创建人: {result['agent']}",
                data=result["data"]
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"]
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档代码生成失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文档代码生成失败: {str(e)}"
        )


@router.get("/agent-info", response_model=ApiResponse)
async def get_agent_info():
    """
    获取当前代码生成Agent信息

    Returns:
        Agent信息

    Examples:
        GET /api/v1/document/agent-info
    """
    try:
        return ApiResponse(
            success=True,
            message="获取Agent信息成功",
            data={
                "agent_name": document_generator.agent_name,
                "description": "HIS系统开发助手，负责根据设计文档生成符合规范的Java代码",
                "supported_formats": [".md", ".docx", ".doc"]
            }
        )
    except Exception as e:
        logger.error(f"获取Agent信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取Agent信息失败: {str(e)}"
        )
