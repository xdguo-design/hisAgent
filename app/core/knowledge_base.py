"""
知识库管理模块

基于LlamaIndex实现知识库的创建、加载、查询和管理。
支持多种向量数据库（当前使用ChromaDB）。
"""

from llama_index.core import VectorStoreIndex, StorageContext, Document, SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter, SemanticSplitterNodeParser, TextSplitter
from llama_index.core.schema import TextNode
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.zhipuai import ZhipuAIEmbedding
import chromadb
from typing import List, Optional, Dict, Any
from app.config import settings
from app.models.database import KnowledgeBase, SessionLocal, ModelConfig
from app.models.schemas import KnowledgeBaseQueryResponse
from app.utils.logger import setup_logger
from app.core.ast_splitter import ASTSplitter
import os

logger = setup_logger(__name__)


class KnowledgeBaseService:
    """
    知识库服务类
    
    提供完整的知识库管理功能：
    1. 创建索引：从文档目录创建向量索引
    2. 加载索引：从持久化存储加载索引
    3. 查询知识库：基于相似度检索相关文档
    4. 管理知识库：列出、删除知识库
    5. 添加文档：向已有索引添加新文档
    
    Attributes:
        embed_model: 文本嵌入模型
        indices: 已加载的索引缓存
        chroma_client: ChromaDB客户端
    """
    
    def __init__(self):
        """
        初始化知识库服务
        
        创建文本嵌入模型和ChromaDB客户端实例。
        """
        # 从数据库获取用户配置的默认API key
        api_key = self._get_default_api_key()
        
        # 默认使用智谱AI的嵌入模型
        self.embed_model = ZhipuAIEmbedding(api_key=api_key, model="embedding-2")
        self.indices: Dict[str, VectorStoreIndex] = {}
        self.chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        
        logger.info("知识库服务初始化成功，使用智谱AI嵌入模型")
    
    def _get_default_api_key(self) -> str:
        """
        从数据库获取用户配置的默认模型API key
        
        Returns:
            用户配置的API key，如果未找到则返回配置文件中的key
        """
        try:
            db = SessionLocal()
            model_config = db.query(ModelConfig).filter(
                ModelConfig.is_default == True,
                ModelConfig.is_active == True
            ).first()
            
            if model_config and model_config.api_key:
                logger.info("使用用户配置的默认模型API key")
                return model_config.api_key
            else:
                logger.warning("未找到用户配置的默认API key，使用配置文件中的key")
                return settings.zhipuai_api_key
        except Exception as e:
            logger.error(f"获取默认API key失败: {e}，使用配置文件中的key")
            return settings.zhipuai_api_key
        finally:
            if db:
                db.close()
    
    def _get_embedding_model(self, model_name: str):
        """
        根据模型名称获取嵌入模型实例
        
        Args:
            model_name: 嵌入模型名称
        
        Returns:
            对应的嵌入模型实例
        """
        # 从数据库获取用户配置的默认API key
        api_key = self._get_default_api_key()
        
        if model_name.startswith("zhipuai") or model_name == "zhipuai-embedding":
            return ZhipuAIEmbedding(api_key=api_key, model="embedding-2")
        elif model_name.startswith("text-embedding"):
            return OpenAIEmbedding(api_key=settings.openai_api_key, model=model_name)
        else:
            # 默认使用智谱AI
            return ZhipuAIEmbedding(api_key=api_key, model="embedding-2")
    
    def _create_nodes(
        self,
        documents: List[Document],
        splitter_type: str,
        chunk_size: int,
        chunk_overlap: int
    ):
        """
        根据分块类型创建文档节点
        
        Args:
            documents: 文档列表
            splitter_type: 分块类型（mixed: 混合策略, ast: AST分块, sentence: 句子级, semantic: 语义级, custom: 自定义）
            chunk_size: 分块大小
            chunk_overlap: 重叠大小
        
        Returns:
            文档节点列表
        """
        if splitter_type == "mixed":
            # 混合策略：根据文件类型自动选择分块方法
            nodes = self._mixed_splitter(documents, chunk_size, chunk_overlap)
            logger.info(f"使用混合策略分块，chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")
        
        elif splitter_type == "ast":
            # AST 分块（用于代码文件）
            ast_splitter = ASTSplitter(max_chunk_size=chunk_size)
            nodes = ast_splitter.split_documents(documents, chunk_size, chunk_overlap)
            logger.info(f"使用AST分块，max_chunk_size={chunk_size}")
        
        elif splitter_type == "sentence":
            # 句子级分块
            splitter = SentenceSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                paragraph_separator="\n\n"
            )
            nodes = splitter.get_nodes_from_documents(documents)
            logger.info(f"使用句子级分块，chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")
        
        elif splitter_type == "semantic":
            # 语义级分块
            api_key = self._get_default_api_key()
            embed_model = ZhipuAIEmbedding(api_key=api_key, model="embedding-2")
            splitter = SemanticSplitterNodeParser(
                buffer_size=1,
                breakpoint_percentile_threshold=95,
                embed_model=embed_model
            )
            nodes = splitter.get_nodes_from_documents(documents)
            logger.info(f"使用语义级分块，breakpoint_percentile_threshold=95")
        
        elif splitter_type == "custom":
            # 自定义分块（按段落分块）
            nodes = self._custom_splitter(documents, chunk_size, chunk_overlap)
            logger.info(f"使用自定义分块，chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")
        
        else:
            # 默认使用混合策略
            nodes = self._mixed_splitter(documents, chunk_size, chunk_overlap)
            logger.warning(f"未知的分块类型 {splitter_type}，使用默认混合策略")
        
        return nodes
    
    def _custom_splitter(
        self,
        documents: List[Document],
        chunk_size: int,
        chunk_overlap: int
    ) -> List:
        """
        自定义分块器（按段落和章节分块）
        
        Args:
            documents: 文档列表
            chunk_size: 最大块大小
            chunk_overlap: 重叠大小
        
        Returns:
            文档节点列表
        """
        nodes = []
        
        for doc in documents:
            text = doc.text
            chunks = []
            
            # 按Markdown标题分块
            sections = text.split("## ")
            
            for section in sections:
                if not section.strip():
                    continue
                
                # 如果章节太长，按段落进一步分块
                if len(section) > chunk_size:
                    paragraphs = section.split("\n\n")
                    current_chunk = ""
                    
                    for para in paragraphs:
                        if len(current_chunk) + len(para) > chunk_size:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                            current_chunk = para
                        else:
                            current_chunk += "\n\n" + para if current_chunk else para
                    
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                else:
                    chunks.append(section.strip())
            
            # 创建节点
            for chunk in chunks:
                if chunk:
                    node = TextNode(
                        text=chunk,
                        metadata=doc.metadata.copy()
                    )
                    nodes.append(node)
        
        return nodes
    
    def _mixed_splitter(
        self,
        documents: List[Document],
        chunk_size: int,
        chunk_overlap: int
    ) -> List:
        """
        混合分块器：根据文件类型自动选择最佳分块方法
        
        策略：
        - 代码文件（.java, .py, .sql）: 使用 AST 分块
        - Markdown 文件：按标题和段落分块
        - 普通文本文件：使用句子级分块
        
        Args:
            documents: 文档列表
            chunk_size: 最大块大小
            chunk_overlap: 重叠大小
        
        Returns:
            文档节点列表
        """
        all_nodes = []
        code_docs = []
        md_docs = []
        text_docs = []
        
        for doc in documents:
            file_path = doc.metadata.get('file_path', '')
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext in ['.java', '.py', '.sql']:
                code_docs.append(doc)
            elif ext in ['.md', '.markdown']:
                md_docs.append(doc)
            else:
                text_docs.append(doc)
        
        # 处理代码文件（AST 分块）
        if code_docs:
            ast_splitter = ASTSplitter(max_chunk_size=chunk_size)
            code_nodes = ast_splitter.split_documents(code_docs, chunk_size, chunk_overlap)
            all_nodes.extend(code_nodes)
        
        # 处理 Markdown 文件（按标题分块）
        if md_docs:
            for doc in md_docs:
                text = doc.text
                sections = text.split("## ")
                
                for section in sections:
                    if not section.strip():
                        continue
                    
                    if len(section) > chunk_size:
                        paragraphs = section.split("\n\n")
                        current_chunk = ""
                        
                        for para in paragraphs:
                            if len(current_chunk) + len(para) > chunk_size:
                                if current_chunk:
                                    node = TextNode(
                                        text=current_chunk.strip(),
                                        metadata={**doc.metadata, 'chunk_type': 'mixed_markdown'}
                                    )
                                    all_nodes.append(node)
                                current_chunk = para
                            else:
                                current_chunk += "\n\n" + para if current_chunk else para
                        
                        if current_chunk:
                            node = TextNode(
                                text=current_chunk.strip(),
                                metadata={**doc.metadata, 'chunk_type': 'mixed_markdown'}
                            )
                            all_nodes.append(node)
                    else:
                        node = TextNode(
                            text=section.strip(),
                            metadata={**doc.metadata, 'chunk_type': 'mixed_markdown'}
                        )
                        all_nodes.append(node)
        
        # 处理普通文本文件（句子级分块）
        if text_docs:
            splitter = SentenceSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                paragraph_separator="\n\n"
            )
            text_nodes = splitter.get_nodes_from_documents(text_docs)
            for node in text_nodes:
                node.metadata['chunk_type'] = 'mixed_sentence'
            all_nodes.extend(text_nodes)
        
        return all_nodes
    
    def create_index(
        self,
        name: str,
        data_path: str,
        chunk_size: int = None,
        chunk_overlap: int = None,
        embedding_model: str = None,
        splitter_type: str = "sentence",
        description: str = None
    ) -> Dict[str, Any]:
        """
        创建知识库索引
        
        从指定路径的文档目录创建向量索引，支持多种文档格式和分块策略。
        
        Args:
            name: 知识库名称（唯一标识）
            data_path: 文档目录路径
            chunk_size: 文本分块大小（字符数）
            chunk_overlap: 文本分块重叠大小（字符数）
            embedding_model: 嵌入模型名称
            splitter_type: 分块类型（sentence: 句子级, semantic: 语义级, custom: 自定义）
            description: 知识库描述
        
        Returns:
            创建结果字典，包含：
            {
                "success": bool,  # 是否成功
                "name": str,      # 知识库名称
                "document_count": int,  # 文档数量
                "message": str    # 提示信息
            }
        
        Raises:
            FileNotFoundError: 数据路径不存在时抛出
            Exception: 其他错误时抛出
        
        Examples:
            >>> service = KnowledgeBaseService()
            >>> result = service.create_index(
            ...     name="my_kb",
            ...     data_path="./docs"
            ... )
            >>> print(result["document_count"])
        """
        try:
            # 验证数据路径
            if not os.path.exists(data_path):
                raise FileNotFoundError(f"数据路径不存在: {data_path}")
            
            if not os.path.isdir(data_path):
                raise ValueError(f"数据路径不是目录: {data_path}")
            
            # 使用默认值
            chunk_size = chunk_size or settings.default_chunk_size
            chunk_overlap = chunk_overlap or settings.default_chunk_overlap
            embedding_model = embedding_model or "zhipuai-embedding"
            
            logger.info(f"开始创建知识库索引: {name}, 路径: {data_path}, 嵌入模型: {embedding_model}")
            
            # 根据模型名称选择嵌入模型
            embed_model = self._get_embedding_model(embedding_model)
            
            # 加载文档
            documents = SimpleDirectoryReader(data_path).load_data()
            
            if not documents:
                logger.warning(f"数据路径中没有找到文档: {data_path}")
                return {
                    "success": False,
                    "name": name,
                    "document_count": 0,
                    "message": "数据路径中没有找到文档"
                }
            
            logger.info(f"加载了 {len(documents)} 个文档")
            
            # 文本分块：根据splitter_type选择分块策略
            nodes = self._create_nodes(documents, splitter_type, chunk_size, chunk_overlap)
            
            logger.info(f"文档分块完成，共 {len(nodes)} 个节点")
            
            # 创建向量存储
            chroma_collection = self.chroma_client.get_or_create_collection(name)
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            
            # 创建索引
            index = VectorStoreIndex(
                nodes=nodes,
                storage_context=storage_context,
                embed_model=embed_model
            )
            
            # 缓存索引
            self.indices[name] = index
            
            # 更新数据库
            db = SessionLocal()
            try:
                kb = KnowledgeBase(
                    name=name,
                    path=data_path,
                    description=description,
                    embedding_model=embedding_model,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    splitter_type=splitter_type,
                    document_count=len(documents),
                    is_active=True
                )
                db.merge(kb)
                db.commit()
            finally:
                db.close()
            
            logger.info(f"知识库索引创建成功: {name}, 文档数: {len(documents)}")
            
            return {
                "success": True,
                "name": name,
                "document_count": len(documents),
                "message": f"成功创建知识库索引，共 {len(documents)} 个文档"
            }
            
        except Exception as e:
            logger.error(f"创建知识库索引失败 {name}: {e}")
            raise
    
    def load_index(self, name: str) -> Optional[VectorStoreIndex]:
        """
        加载知识库索引
        
        从持久化存储中加载已有的知识库索引。
        
        Args:
            name: 知识库名称
        
        Returns:
            加载的索引对象，如果不存在则返回None
        
        Examples:
            >>> service = KnowledgeBaseService()
            >>> index = service.load_index("my_kb")
            >>> if index:
            ...     print("索引加载成功")
        """
        try:
            # 检查缓存
            if name in self.indices:
                logger.debug(f"从缓存加载索引: {name}")
                return self.indices[name]
            
            # 检查集合是否存在
            collections = self.chroma_client.list_collections()
            collection_names = [col.name for col in collections]
            
            if name not in collection_names:
                logger.warning(f"知识库不存在: {name}")
                return None
            
            # 加载索引
            chroma_collection = self.chroma_client.get_collection(name)
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            
            index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store,
                storage_context=storage_context,
                embed_model=self.embed_model
            )
            
            # 缓存索引
            self.indices[name] = index
            
            logger.info(f"知识库索引加载成功: {name}")
            return index
            
        except Exception as e:
            logger.error(f"加载知识库索引失败 {name}: {e}")
            return None
    
    def query(
        self,
        index_name: str,
        query: str,
        top_k: int = None,
        similarity_threshold: float = None
    ) -> KnowledgeBaseQueryResponse:
        """
        查询知识库
        
        基于语义相似度检索知识库中的相关文档。
        
        Args:
            index_name: 知识库名称
            query: 查询内容
            top_k: 返回的最相关文档数量
            similarity_threshold: 相似度阈值，低于此值的文档将被过滤
        
        Returns:
            查询响应对象，包含：
            - answer: 生成的回答
            - sources: 来源文件列表
            - similarity_scores: 相似度分数列表
        
        Raises:
            ValueError: 知识库不存在时抛出
        
        Examples:
            >>> service = KnowledgeBaseService()
            >>> response = service.query("my_kb", "什么是HIS系统？")
            >>> print(response.answer)
        """
        try:
            # 使用默认值
            top_k = top_k or settings.default_top_k
            similarity_threshold = similarity_threshold or 0.7
            
            # 加载索引
            index = self.load_index(index_name)
            if not index:
                raise ValueError(f"知识库不存在: {index_name}")
            
            # 根据配置创建查询引擎
            retrieval_type = settings.default_retrieval_type
            
            if retrieval_type == "hybrid":
                query_engine = index.as_query_engine(
                    vector_store_query_mode="hybrid",
                    similarity_top_k=top_k,
                    similarity_cutoff=similarity_threshold,
                    alpha=0.5
                )
                logger.info(f"使用混合检索模式查询知识库: {index_name}")
            else:
                query_engine = index.as_query_engine(
                    vector_store_query_mode="default",
                    similarity_top_k=top_k,
                    similarity_cutoff=similarity_threshold
                )
                logger.info(f"使用HNSW向量检索模式查询知识库: {index_name}")
            
            # 执行查询
            response = query_engine.query(query)
            
            # 提取来源文件
            sources = []
            similarity_scores = []
            
            for node in response.source_nodes:
                # 从元数据中提取文件名
                file_name = node.metadata.get("file_name", "unknown")
                sources.append(file_name)
                
                # 提取相似度分数（如果可用）
                if hasattr(node, "score") and node.score is not None:
                    similarity_scores.append(float(node.score))
            
            logger.info(
                f"知识库查询完成 - 知识库: {index_name}, "
                f"返回结果数: {len(sources)}"
            )
            
            return KnowledgeBaseQueryResponse(
                answer=str(response),
                sources=sources,
                similarity_scores=similarity_scores if similarity_scores else None
            )
            
        except Exception as e:
            logger.error(f"查询知识库失败 {index_name}: {e}")
            raise
    
    def list_collections(self) -> List[str]:
        """
        列出所有知识库
        
        Returns:
            知识库名称列表
        
        Examples:
            >>> service = KnowledgeBaseService()
            >>> collections = service.list_collections()
            >>> for name in collections:
            ...     print(name)
        """
        try:
            collections = self.chroma_client.list_collections()
            return [collection.name for collection in collections]
        except Exception as e:
            logger.error(f"列出知识库失败: {e}")
            return []
    
    def delete_index(self, name: str) -> bool:
        """
        删除知识库索引
        
        Args:
            name: 知识库名称
        
        Returns:
            删除成功返回True，失败返回False
        
        Examples:
            >>> service = KnowledgeBaseService()
            >>> success = service.delete_index("my_kb")
        """
        try:
            # 从缓存中移除
            if name in self.indices:
                del self.indices[name]
            
            # 删除向量集合
            self.chroma_client.delete_collection(name)
            
            # 更新数据库
            db = SessionLocal()
            try:
                kb = db.query(KnowledgeBase).filter(KnowledgeBase.name == name).first()
                if kb:
                    db.delete(kb)
                    db.commit()
            finally:
                db.close()
            
            logger.info(f"知识库删除成功: {name}")
            return True
            
        except Exception as e:
            logger.error(f"删除知识库失败 {name}: {e}")
            return False
    
    def add_documents(
        self,
        index_name: str,
        documents: List[Document]
    ) -> bool:
        """
        向知识库添加文档
        
        Args:
            index_name: 知识库名称
            documents: 要添加的文档列表
        
        Returns:
            添加成功返回True，失败返回False
        
        Examples:
            >>> from llama_index.core import Document
            >>> service = KnowledgeBaseService()
            >>> doc = Document(text="新文档内容")
            >>> service.add_documents("my_kb", [doc])
        """
        try:
            index = self.load_index(index_name)
            if not index:
                raise ValueError(f"知识库不存在: {index_name}")
            
            # 添加文档
            for doc in documents:
                index.insert(doc)
            
            # 更新数据库中的文档计数
            db = SessionLocal()
            try:
                kb = db.query(KnowledgeBase).filter(KnowledgeBase.name == index_name).first()
                if kb:
                    kb.document_count += len(documents)
                    db.commit()
            finally:
                db.close()
            
            logger.info(f"成功添加 {len(documents)} 个文档到 {index_name}")
            return True
            
        except Exception as e:
            logger.error(f"添加文档失败 {index_name}: {e}")
            return False
    
    def get_documents(self, index_name: str) -> List[Dict[str, Any]]:
        """
        获取知识库中的文档列表
        
        Args:
            index_name: 知识库名称
        
        Returns:
            文档信息列表，每个文档包含：
            - doc_id: 文档ID
            - file_name: 文件名
            - metadata: 元数据
        
        Examples:
            >>> service = KnowledgeBaseService()
            >>> docs = service.get_documents("my_kb")
            >>> for doc in docs:
            ...     print(doc["file_name"])
        """
        try:
            collections = self.chroma_client.list_collections()
            collection_names = [col.name for col in collections]
            
            if index_name not in collection_names:
                logger.warning(f"知识库不存在: {index_name}")
                return []
            
            chroma_collection = self.chroma_client.get_collection(index_name)
            
            # 获取所有文档的元数据
            results = chroma_collection.get(include=["metadatas"])
            
            # 使用字典去重（按文件名）
            unique_docs = {}
            for metadata in results["metadatas"]:
                file_name = metadata.get("file_name", "unknown")
                doc_id = metadata.get("doc_id", "")
                
                if file_name not in unique_docs:
                    unique_docs[file_name] = {
                        "doc_id": doc_id,
                        "file_name": file_name,
                        "metadata": metadata
                    }
            
            docs_list = list(unique_docs.values())
            logger.info(f"获取知识库 {index_name} 的文档列表，共 {len(docs_list)} 个文档")
            return docs_list
            
        except Exception as e:
            logger.error(f"获取文档列表失败 {index_name}: {e}")
            return []
    
    def delete_documents(self, index_name: str, file_names: List[str]) -> Dict[str, Any]:
        """
        删除知识库中的文档
        
        Args:
            index_name: 知识库名称
            file_names: 要删除的文件名列表
        
        Returns:
            删除结果字典，包含：
            {
                "success": bool,  # 是否成功
                "deleted_count": int,  # 删除的文档数量
                "message": str    # 提示信息
            }
        
        Examples:
            >>> service = KnowledgeBaseService()
            >>> result = service.delete_documents("my_kb", ["doc1.pdf", "doc2.txt"])
        """
        try:
            collections = self.chroma_client.list_collections()
            collection_names = [col.name for col in collections]
            
            if index_name not in collection_names:
                logger.warning(f"知识库不存在: {index_name}")
                return {
                    "success": False,
                    "deleted_count": 0,
                    "message": f"知识库不存在: {index_name}"
                }
            
            chroma_collection = self.chroma_client.get_collection(index_name)
            
            # 获取所有文档的元数据
            results = chroma_collection.get(include=["metadatas"])
            
            # 收集要删除的文档ID
            ids_to_delete = []
            for i, metadata in enumerate(results["metadatas"]):
                file_name = metadata.get("file_name", "")
                if file_name in file_names:
                    ids_to_delete.append(results["ids"][i])
            
            if not ids_to_delete:
                return {
                    "success": False,
                    "deleted_count": 0,
                    "message": "未找到指定的文档"
                }
            
            # 删除文档
            chroma_collection.delete(ids=ids_to_delete)
            
            # 更新数据库中的文档计数
            db = SessionLocal()
            try:
                kb = db.query(KnowledgeBase).filter(KnowledgeBase.name == index_name).first()
                if kb:
                    kb.document_count = max(0, kb.document_count - len(file_names))
                    db.commit()
            finally:
                db.close()
            
            logger.info(f"成功从知识库 {index_name} 删除 {len(file_names)} 个文档")
            
            return {
                "success": True,
                "deleted_count": len(file_names),
                "message": f"成功删除 {len(file_names)} 个文档"
            }
            
        except Exception as e:
            logger.error(f"删除文档失败 {index_name}: {e}")
            return {
                "success": False,
                "deleted_count": 0,
                "message": f"删除文档失败: {str(e)}"
            }
    
    def create_index_from_files(
        self,
        name: str,
        file_paths: List[str],
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        embedding_model: str = "zhipuai-embedding",
        splitter_type: str = "sentence",
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        从文件列表创建知识库索引
        
        Args:
            name: 知识库名称（唯一标识）
            file_paths: 文件路径列表
            chunk_size: 文本分块大小（字符数）
            chunk_overlap: 文本分块重叠大小（字符数）
            embedding_model: 嵌入模型名称
            splitter_type: 分块类型（sentence: 句子级, semantic: 语义级, custom: 自定义）
            description: 知识库描述
        
        Returns:
            创建结果字典，包含：
            {
                "success": bool,  # 是否成功
                "name": str,      # 知识库名称
                "document_count": int,  # 文档数量
                "message": str    # 提示信息
            }
        """
        try:
            if not file_paths:
                raise ValueError("文件列表为空")
            
            # 验证文件是否存在
            valid_files = []
            for file_path in file_paths:
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    valid_files.append(file_path)
                else:
                    logger.warning(f"文件不存在，跳过: {file_path}")
            
            if not valid_files:
                raise ValueError("没有有效的文件")
            
            logger.info(f"开始从 {len(valid_files)} 个文件创建知识库索引: {name}")
            
            # 根据模型名称选择嵌入模型
            embed_model = self._get_embedding_model(embedding_model)
            
            # 加载文档
            documents = SimpleDirectoryReader(input_files=valid_files).load_data()
            
            if not documents:
                logger.warning("没有从文件中加载到文档")
                return {
                    "success": False,
                    "name": name,
                    "document_count": 0,
                    "message": "没有从文件中加载到文档"
                }
            
            logger.info(f"加载了 {len(documents)} 个文档")
            
            # 文本分块：根据splitter_type选择分块策略
            nodes = self._create_nodes(documents, splitter_type, chunk_size, chunk_overlap)
            
            logger.info(f"文档分块完成，共 {len(nodes)} 个节点")
            
            # 创建向量存储
            chroma_collection = self.chroma_client.get_or_create_collection(name)
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            
            # 创建索引
            index = VectorStoreIndex(
                nodes=nodes,
                storage_context=storage_context,
                embed_model=embed_model
            )
            
            # 缓存索引
            self.indices[name] = index
            
            # 更新数据库
            db = SessionLocal()
            try:
                kb = KnowledgeBase(
                    name=name,
                    path=",".join(valid_files),
                    description=description,
                    embedding_model=embedding_model,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    splitter_type=splitter_type,
                    document_count=len(documents),
                    is_active=True
                )
                db.merge(kb)
                db.commit()
            finally:
                db.close()
            
            logger.info(f"知识库索引创建成功: {name}, 文档数: {len(documents)}")
            
            return {
                "success": True,
                "name": name,
                "document_count": len(documents),
                "message": f"成功创建知识库索引，共 {len(documents)} 个文档"
            }
            
        except Exception as e:
            logger.error(f"从文件创建知识库索引失败 {name}: {e}")
            raise
    
    def get_kb_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取知识库信息
        
        Args:
            name: 知识库名称
        
        Returns:
            知识库信息字典，如果不存在则返回None
        """
        db = SessionLocal()
        try:
            kb = db.query(KnowledgeBase).filter(KnowledgeBase.name == name).first()
            if kb:
                return {
                    "name": kb.name,
                    "path": kb.path,
                    "description": kb.description,
                    "embedding_model": kb.embedding_model,
                    "chunk_size": kb.chunk_size,
                    "chunk_overlap": kb.chunk_overlap,
                    "document_count": kb.document_count,
                    "is_active": kb.is_active,
                    "created_at": kb.created_at.isoformat(),
                    "updated_at": kb.updated_at.isoformat()
                }
            return None
        finally:
            db.close()
    
    def list_kb_info(self) -> List[Dict[str, Any]]:
        """
        列出所有知识库信息
        
        Returns:
            知识库信息列表
        """
        db = SessionLocal()
        try:
            kbs = db.query(KnowledgeBase).filter(KnowledgeBase.is_active == True).all()
            return [
                {
                    "name": kb.name,
                    "path": kb.path,
                    "description": kb.description,
                    "document_count": kb.document_count,
                    "created_at": kb.created_at.isoformat()
                }
                for kb in kbs
            ]
        finally:
            db.close()


# 全局知识库服务实例
knowledge_base_service = KnowledgeBaseService()
