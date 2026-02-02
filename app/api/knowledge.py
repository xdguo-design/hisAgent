"""
知识库管理API路由

提供知识库的创建、查询、管理等功能接口。
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional, List
import os
import shutil
import uuid
from app.models.database import get_db
from app.models.schemas import (
    ApiResponse,
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    KnowledgeBaseQueryRequest,
    KnowledgeBaseQueryResponse,
    DocumentUploadResponse,
    CreateIndexFromFilesRequest,
    AddDocumentsRequest,
    DocumentInfo,
    DeleteDocumentsRequest,
    DeleteDocumentsResponse
)
from app.core.knowledge_base import knowledge_base_service
from app.models.database import KnowledgeBase
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/knowledge", tags=["知识库管理"])


@router.post("/create", response_model=ApiResponse)
async def create_knowledge_base(
    kb_data: KnowledgeBaseCreate,
    db: Session = Depends(get_db)
):
    """
    创建知识库
    
    从指定路径的文档目录创建向量知识库。
    
    Args:
        kb_data: 知识库配置数据
    
    Returns:
        创建结果
    
    Examples:
        POST /api/v1/knowledge/create
        {
            "name": "his_knowledge",
            "path": "./docs/his",
            "description": "HIS系统知识文档"
        }
    """
    try:
        # 检查知识库名称是否已存在
        existing = db.query(KnowledgeBase).filter(KnowledgeBase.name == kb_data.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"知识库名称已存在: {kb_data.name}"
            )
        
        # 创建索引
        result = knowledge_base_service.create_index(
            name=kb_data.name,
            data_path=kb_data.path,
            chunk_size=kb_data.chunk_size,
            chunk_overlap=kb_data.chunk_overlap,
            embedding_model=kb_data.embedding_model,
            splitter_type=kb_data.splitter_type,
            description=kb_data.description
        )
        
        if result["success"]:
            return ApiResponse(
                success=True,
                message=result["message"],
                data={
                    "name": result["name"],
                    "document_count": result["document_count"]
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建知识库失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建知识库失败: {str(e)}"
        )


@router.get("/list", response_model=list[KnowledgeBaseResponse])
async def list_knowledge_bases(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    列出知识库
    
    支持分页和状态筛选。
    
    Args:
        skip: 跳过的记录数
        limit: 返回的最大记录数
        is_active: 是否启用筛选
    
    Returns:
        知识库列表
    
    Examples:
        GET /api/v1/knowledge/list?skip=0&limit=10&is_active=true
    """
    try:
        query = db.query(KnowledgeBase)
        
        if is_active is not None:
            query = query.filter(KnowledgeBase.is_active == is_active)
        
        kbs = query.offset(skip).limit(limit).all()
        
        return [KnowledgeBaseResponse.model_validate(kb) for kb in kbs]
        
    except Exception as e:
        logger.error(f"列出知识库失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"列出知识库失败: {str(e)}"
        )


@router.get("/{name}", response_model=ApiResponse)
async def get_knowledge_base(name: str):
    """
    获取知识库信息
    
    Args:
        name: 知识库名称
    
    Returns:
        知识库信息
    
    Examples:
        GET /api/v1/knowledge/his_knowledge
    """
    try:
        kb_info = knowledge_base_service.get_kb_info(name)
        if not kb_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"知识库不存在: {name}"
            )
        
        return ApiResponse(
            success=True,
            message="获取知识库信息成功",
            data=kb_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取知识库信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识库信息失败: {str(e)}"
        )


@router.post("/{name}/query", response_model=KnowledgeBaseQueryResponse)
async def query_knowledge_base(
    name: str,
    request: KnowledgeBaseQueryRequest
):
    """
    查询知识库
    
    基于语义相似度检索知识库中的相关文档。
    
    Args:
        name: 知识库名称
        request: 查询请求
    
    Returns:
        查询结果，包含回答和来源文档
    
    Examples:
        POST /api/v1/knowledge/his_knowledge/query
        {
            "query": "什么是HL7标准？",
            "top_k": 5,
            "similarity_threshold": 0.7
        }
    """
    try:
        result = knowledge_base_service.query(
            index_name=name,
            query=request.query,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold
        )
        
        return result
        
    except Exception as e:
        logger.error(f"查询知识库失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询知识库失败: {str(e)}"
        )


@router.delete("/{name}")
async def delete_knowledge_base(name: str):
    """
    删除知识库
    
    Args:
        name: 知识库名称
    
    Returns:
        删除结果
    
    Examples:
        DELETE /api/v1/knowledge/his_knowledge
    """
    try:
        success = knowledge_base_service.delete_index(name)
        if success:
            return ApiResponse(
                success=True,
                message=f"知识库删除成功: {name}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"知识库不存在或删除失败: {name}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除知识库失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除知识库失败: {str(e)}"
        )


@router.put("/{name}")
async def update_knowledge_base(
    name: str,
    update_data: KnowledgeBaseUpdate,
    db: Session = Depends(get_db)
):
    """
    更新知识库配置
    
    Args:
        name: 知识库名称
        update_data: 更新数据
    
    Returns:
        更新结果
    
    Examples:
        PUT /api/v1/knowledge/his_knowledge
        {
            "description": "更新后的描述"
        }
    """
    try:
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.name == name).first()
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"知识库不存在: {name}"
            )
        
        # 更新字段
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            if hasattr(kb, key):
                setattr(kb, key, value)
        
        db.commit()
        db.refresh(kb)
        
        logger.info(f"更新知识库成功: {name}")
        
        return ApiResponse(
            success=True,
            message=f"知识库更新成功: {name}",
            data=KnowledgeBaseResponse.model_validate(kb).model_dump()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新知识库失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新知识库失败: {str(e)}"
        )


@router.post("/{name}/rebuild")
async def rebuild_knowledge_base(name: str):
    """
    重建知识库索引
    
    删除现有索引并重新创建。
    
    Args:
        name: 知识库名称
    
    Returns:
        重建结果
    
    Examples:
        POST /api/v1/knowledge/his_knowledge/rebuild
    """
    try:
        # 获取知识库信息
        kb_info = knowledge_base_service.get_kb_info(name)
        if not kb_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"知识库不存在: {name}"
            )
        
        # 检查数据路径是否存在
        data_path = kb_info.get("path", "")
        if data_path and not os.path.exists(data_path):
            logger.warning(f"重建知识库失败: 原始数据路径不存在 - {data_path}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无法重建知识库：原始文档路径不存在（{data_path}）。\n\n提示：\n1. 如果文件已移动或删除，请使用'添加文档'功能重新上传\n2. 如果路径发生变化，请删除知识库后重新创建"
            )
        
        # 删除现有索引
        logger.info(f"删除知识库 {name} 的现有索引...")
        knowledge_base_service.delete_index(name)
        
        # 重新创建索引
        logger.info(f"重新创建知识库 {name} 的索引...")
        result = knowledge_base_service.create_index(
            name=name,
            data_path=kb_info["path"],
            chunk_size=kb_info["chunk_size"],
            chunk_overlap=kb_info["chunk_overlap"],
            embedding_model=kb_info["embedding_model"],
            description=kb_info["description"]
        )
        
        if result["success"]:
            return ApiResponse(
                success=True,
                message=f"知识库重建成功: {name}",
                data={
                    "name": result["name"],
                    "document_count": result["document_count"]
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重建知识库失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重建知识库失败: {str(e)}"
        )


@router.post("/upload", response_model=ApiResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    上传文档
    
    上传文档文件到服务器临时存储目录。
    
    Args:
        file: 上传的文件对象
    
    Returns:
        上传结果
    
    Examples:
        POST /api/v1/knowledge/upload
        Content-Type: multipart/form-data
    """
    try:
        logger.info(f"========== 开始处理文件上传 ==========")
        logger.info(f"文件对象: {file}")
        logger.info(f"文件名: {file.filename}")
        
        if not file.filename:
            logger.error("文件名为空")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件名不能为空"
            )
        
        # 检查文件扩展名
        allowed_extensions = {'.txt', '.md', '.pdf', '.docx', '.doc', '.html', '.json', '.java'}
        # 处理文件夹上传时可能包含路径的文件名
        original_filename = file.filename
        filename_only = os.path.basename(original_filename)
        file_ext = os.path.splitext(filename_only)[1].lower()
        
        logger.info(f"原始文件名: {original_filename}")
        logger.info(f"文件名: {filename_only}")
        logger.info(f"扩展名: '{file_ext}'")
        logger.info(f"支持的扩展名: {allowed_extensions}")
        
        if file_ext not in allowed_extensions:
            error_msg = f"不支持的文件类型: '{file_ext}'，文件名: {filename_only}。仅支持: {', '.join(allowed_extensions)}"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # 创建上传目录
        upload_dir = os.path.join(os.getcwd(), "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        
        # 生成唯一文件名
        file_id = str(uuid.uuid4())
        filename = f"{file_id}{file_ext}"
        file_path = os.path.join(upload_dir, filename)
        
        # 保存文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = os.path.getsize(file_path)
        
        logger.info(f"文件上传成功: {original_filename} -> {filename} ({file_size} bytes)")
        
        return ApiResponse(
            success=True,
            message="文件上传成功",
            data=DocumentUploadResponse(
                filename=filename_only,
                size=file_size,
                path=file_path,
                status="uploaded"
            ).model_dump()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件上传失败: {str(e)}"
        )


@router.post("/create-from-files", response_model=ApiResponse)
async def create_index_from_files(
    request: CreateIndexFromFilesRequest,
    db: Session = Depends(get_db)
):
    """
    从上传的文件创建知识库
    
    使用上传的文件创建向量知识库。
    
    Args:
        request: 创建索引请求
    
    Returns:
        创建结果
    
    Examples:
        POST /api/v1/knowledge/create-from-files
        {
            "name": "his_knowledge",
            "description": "HIS系统知识文档",
            "chunk_size": 512,
            "chunk_overlap": 50
        }
    """
    try:
        # 检查知识库名称是否已存在
        existing = db.query(KnowledgeBase).filter(KnowledgeBase.name == request.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"知识库名称已存在: {request.name}"
            )
        
        # 获取上传目录中的所有文件
        upload_dir = os.path.join(os.getcwd(), "uploads")
        if not os.path.exists(upload_dir):
            logger.error(f"上传目录不存在: {upload_dir}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="上传目录不存在，请重新上传文件"
            )
        
        file_paths = [
            os.path.join(upload_dir, f) 
            for f in os.listdir(upload_dir) 
            if os.path.isfile(os.path.join(upload_dir, f))
        ]
        
        if not file_paths:
            logger.error("在上传目录中没有找到文件")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有找到已上传的文件，请先选择文件并点击上传"
            )
        
        # 创建索引
        result = knowledge_base_service.create_index_from_files(
            name=request.name,
            file_paths=file_paths,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            embedding_model=request.embedding_model,
            splitter_type=request.splitter_type,
            description=request.description,
            check_duplicates=True
        )
        
        if result["success"]:
            # 清理上传的文件
            for file_path in file_paths:
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.warning(f"清理文件失败: {file_path}, {e}")
            
            return ApiResponse(
                success=True,
                message=result["message"],
                data={
                    "name": result["name"],
                    "document_count": result["document_count"]
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"从文件创建知识库失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"从文件创建知识库失败: {str(e)}"
        )


@router.post("/add-documents", response_model=ApiResponse)
async def add_documents_to_kb(
    request: AddDocumentsRequest,
    db: Session = Depends(get_db)
):
    """
    向已有知识库添加文档
    
    从上传目录的文件向指定知识库添加新文档。
    
    Args:
        request: 添加文档请求
    
    Returns:
        添加结果
    
    Examples:
        POST /api/v1/knowledge/add-documents
        {
            "name": "his_knowledge",
            "chunk_size": 512,
            "chunk_overlap": 50
        }
    """
    try:
        from llama_index.core import Document
        
        logger.info(f"========== 开始添加文档到知识库 {request.name} ==========")
        
        # 检查知识库是否存在
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.name == request.name).first()
        if not kb:
            logger.error(f"知识库不存在: {request.name}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"知识库不存在: {request.name}"
            )
        logger.info(f"知识库 {request.name} 存在，当前文档数: {kb.document_count}")
        
        # 获取上传目录中的所有文件
        upload_dir = os.path.join(os.getcwd(), "uploads")
        if not os.path.exists(upload_dir):
            logger.error(f"上传目录不存在: {upload_dir}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="上传目录不存在，请重新上传文件"
            )
        
        file_paths = [
            os.path.join(upload_dir, f) 
            for f in os.listdir(upload_dir) 
            if os.path.isfile(os.path.join(upload_dir, f))
        ]
        
        if not file_paths:
            logger.error("在上传目录中没有找到文件")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有找到已上传的文件，请先选择文件并点击上传"
            )
        
        logger.info(f"找到 {len(file_paths)} 个上传文件")
        
        # 检查文件大小（限制单个文件50MB）
        MAX_FILE_SIZE = 50 * 1024 * 1024
        total_size = 0
        valid_files = []
        for file_path in file_paths:
            file_size = os.path.getsize(file_path)
            total_size += file_size
            if file_size > MAX_FILE_SIZE:
                logger.warning(f"文件过大，跳过: {os.path.basename(file_path)} ({file_size / 1024 / 1024:.2f}MB)")
            else:
                valid_files.append(file_path)
        
        if not valid_files:
            logger.error("所有文件都因过大而被跳过")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"没有有效的文件（单个文件不能超过50MB）"
            )
        
        logger.info(f"有效文件数: {len(valid_files)}，总大小: {total_size / 1024 / 1024:.2f}MB")
        
        # 使用知识库原有的embedding模型
        embedding_model = request.embedding_model or kb.embedding_model
        
        # 检查重复文件名并记录
        existing_files = set()
        file_name_map = {}
        for file_path in valid_files:
            file_name = os.path.basename(file_path)
            if file_name in existing_files:
                logger.warning(f"发现重复文件名: {file_name}")
            existing_files.add(file_name)
            file_name_map[file_name] = file_path
        
        # 加载文档
        documents = []
        for i, file_path in enumerate(valid_files):
            try:
                logger.info(f"正在加载文件 {i+1}/{len(valid_files)}: {os.path.basename(file_path)}")
                ext = os.path.splitext(file_path)[1].lower()
                if ext == '.pdf':
                    from llama_index.core.readers import SimpleDirectoryReader
                    docs = SimpleDirectoryReader(input_files=[file_path]).load_data()
                    documents.extend(docs)
                elif ext in ['.docx', '.doc']:
                    from llama_index.core.readers import SimpleDirectoryReader
                    docs = SimpleDirectoryReader(input_files=[file_path]).load_data()
                    documents.extend(docs)
                elif ext == '.json':
                    import json
                    with open(file_path, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                    if isinstance(json_data, list):
                        for item in json_data:
                            documents.append(Document(text=str(item)))
                    elif isinstance(json_data, dict):
                        documents.append(Document(text=json.dumps(json_data, ensure_ascii=False)))
                    else:
                        documents.append(Document(text=str(json_data)))
                else:
                    from llama_index.core.readers import SimpleDirectoryReader
                    docs = SimpleDirectoryReader(input_files=[file_path]).load_data()
                    documents.extend(docs)
                logger.info(f"文件加载成功: {os.path.basename(file_path)}，文档数: {len(documents)}")
            except Exception as e:
                logger.warning(f"加载文件失败 {file_path}: {e}")
                continue
        
        if not documents:
            logger.error("所有上传的文件都加载失败或内容为空")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无法加载上传的文档，请检查文件格式是否正确且内容不为空"
            )
        
        logger.info(f"总文档数: {len(documents)}")
        
        # 使用知识库服务的分块逻辑
        logger.info("开始文档分块...")
        nodes = knowledge_base_service._create_nodes(
            documents=documents,
            splitter_type=kb.splitter_type,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap
        )
        logger.info(f"文档分块完成，共 {len(nodes)} 个节点")
        
        # 添加节点到知识库
        logger.info("开始将节点添加到知识库...")
        success = knowledge_base_service.add_nodes(
            index_name=request.name,
            nodes=nodes
        )
        
        if success:
            # 刷新知识库信息以获取最新的文档计数
            db.refresh(kb)
            
            # 清理上传的文件
            logger.info("清理上传文件...")
            for file_path in file_paths:
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.warning(f"清理文件失败: {file_path}, {e}")
            
            logger.info(f"========== 文档添加完成 ==========")
            return ApiResponse(
                success=True,
                message=f"成功添加 {len(nodes)} 个节点到知识库 {request.name}",
                data={
                    "name": request.name,
                    "document_count": len(nodes),
                    "total_documents": kb.document_count
                }
            )
        else:
            logger.error("添加节点到知识库失败")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="添加文档失败"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加文档失败: {e}", exc_info=True)
        
        # 检查是否是智谱AI API余额不足错误
        error_str = str(e)
        if '余额不足' in error_str or '429' in error_str or '1113' in error_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="智谱AI API余额不足或无可用资源包。请登录智谱AI平台充值或检查账户余额。"
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加文档失败: {str(e)}"
        )


@router.get("/{name}/documents", response_model=ApiResponse)
async def list_documents(name: str):
    """
    获取知识库中的文档列表
    
    Args:
        name: 知识库名称
    
    Returns:
        文档列表
    
    Examples:
        GET /api/v1/knowledge/his_knowledge/documents
    """
    try:
        documents = knowledge_base_service.get_documents(name)
        
        return ApiResponse(
            success=True,
            message=f"获取文档列表成功，共 {len(documents)} 个文档",
            data=documents
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文档列表失败: {str(e)}"
        )


@router.post("/{name}/documents/delete", response_model=ApiResponse)
async def delete_documents(name: str, request: DeleteDocumentsRequest):
    """
    删除知识库中的文档
    
    Args:
        name: 知识库名称
        request: 删除文档请求
    
    Returns:
        删除结果
    
    Examples:
        POST /api/v1/knowledge/his_knowledge/documents/delete
        {
            "name": "his_knowledge",
            "file_names": ["doc1.pdf", "doc2.txt"]
        }
    """
    try:
        # 验证知识库名称
        if name != request.name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="知识库名称不匹配"
            )
        
        result = knowledge_base_service.delete_documents(
            index_name=name,
            file_names=request.file_names
        )
        
        return ApiResponse(
            success=result["success"],
            message=result["message"],
            data={
                "deleted_count": result["deleted_count"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除文档失败: {str(e)}"
        )
