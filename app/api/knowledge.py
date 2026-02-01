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
        
        # 删除现有索引
        knowledge_base_service.delete_index(name)
        
        # 重新创建索引
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
        # 检查文件扩展名
        allowed_extensions = {'.txt', '.md', '.pdf', '.docx', '.doc', '.html', '.json'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件类型: {file_ext}。支持的类型: {', '.join(allowed_extensions)}"
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
        
        logger.info(f"文件上传成功: {file.filename} -> {filename} ({file_size} bytes)")
        
        return ApiResponse(
            success=True,
            message="文件上传成功",
            data=DocumentUploadResponse(
                filename=file.filename,
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="上传目录不存在，请先上传文件"
            )
        
        file_paths = [
            os.path.join(upload_dir, f) 
            for f in os.listdir(upload_dir) 
            if os.path.isfile(os.path.join(upload_dir, f))
        ]
        
        if not file_paths:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有找到上传的文件"
            )
        
        # 创建索引
        result = knowledge_base_service.create_index_from_files(
            name=request.name,
            file_paths=file_paths,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            embedding_model=request.embedding_model,
            splitter_type=request.splitter_type,
            description=request.description
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
        
        # 检查知识库是否存在
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.name == request.name).first()
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"知识库不存在: {request.name}"
            )
        
        # 获取上传目录中的所有文件
        upload_dir = os.path.join(os.getcwd(), "uploads")
        if not os.path.exists(upload_dir):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="上传目录不存在，请先上传文件"
            )
        
        file_paths = [
            os.path.join(upload_dir, f) 
            for f in os.listdir(upload_dir) 
            if os.path.isfile(os.path.join(upload_dir, f))
        ]
        
        if not file_paths:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有找到上传的文件"
            )
        
        # 使用知识库原有的embedding模型
        embedding_model = request.embedding_model or kb.embedding_model
        
        # 加载文档
        documents = []
        for file_path in file_paths:
            try:
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
            except Exception as e:
                logger.warning(f"加载文件失败 {file_path}: {e}")
                continue
        
        if not documents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有成功加载任何文档"
            )
        
        # 文档分块
        from llama_index.core.node_parser import SentenceSplitter
        node_parser = SentenceSplitter(
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap
        )
        nodes = node_parser.get_nodes_from_documents(documents)
        
        # 创建文档对象
        from llama_index.core import Document
        chunked_docs = []
        for node in nodes:
            chunked_docs.append(Document(text=node.text, metadata=node.metadata))
        
        # 添加到知识库
        success = knowledge_base_service.add_documents(
            index_name=request.name,
            documents=chunked_docs
        )
        
        if success:
            # 清理上传的文件
            for file_path in file_paths:
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.warning(f"清理文件失败: {file_path}, {e}")
            
            return ApiResponse(
                success=True,
                message=f"成功添加 {len(chunked_docs)} 个文档到知识库 {request.name}",
                data={
                    "name": request.name,
                    "document_count": len(chunked_docs),
                    "total_documents": kb.document_count + len(chunked_docs)
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="添加文档失败"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加文档失败: {e}")
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
