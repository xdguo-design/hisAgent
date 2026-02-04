"""
LLM相关API路由

提供LLM对话、模型管理等功能接口。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import json
import httpx
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


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    对话接口（支持流式输出）
    
    发送对话请求。根据stream参数返回完整回复或流式输出。
    
    Args:
        request: 对话请求，包含消息列表和配置选项
    
    Returns:
        如果stream=False，返回ChatResponse（完整回复）
        如果stream=True，返回StreamingResponse（SSE流式输出）
    
    Examples:
        POST /api/v1/llm/chat
        {
            "messages": [
                {"role": "user", "content": "你好"}
            ],
            "model_config_name": "default",
            "stream": true
        }
    """
    try:
        # 转换消息格式
        messages = [{"role": msg.role.value, "content": msg.content} for msg in request.messages]
        
        # 如果请求流式输出
        if request.stream:
            # 转换消息格式
            messages = [{"role": msg.role.value, "content": msg.content} for msg in request.messages]
            
            # 获取模型配置
            from app.models.database import SessionLocal
            from app.models.database import ModelConfig
            db = SessionLocal()
            
            try:
                # 获取模型配置
                if request.model_config_name:
                    model_config = db.query(ModelConfig).filter(
                        ModelConfig.name == request.model_config_name,
                        ModelConfig.is_active == True
                    ).first()
                else:
                    model_config = db.query(ModelConfig).filter(
                        ModelConfig.is_default == True,
                        ModelConfig.is_active == True
                    ).first()
                
                # 准备调用参数
                chat_params = {
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "top_p": 0.9,
                    "stream": True
                }
                
                if model_config:
                    chat_params["model"] = model_config.model_name
                    chat_params["temperature"] = model_config.temperature
                    chat_params["max_tokens"] = model_config.max_tokens
                    chat_params["top_p"] = model_config.top_p
                else:
                    chat_params["model"] = "glm-4"
                
                # 获取用户消息（用于提示词模板）
                user_message = ""
                for msg in reversed(messages):
                    if msg.get("role") == "user":
                        user_message = msg.get("content", "")
                        break
                
                # 如果有知识库，使用RAG查询
                if request.knowledge_base_name:
                    if user_message:
                        from app.core.agentic_rag import AgenticRAG, AgenticRAGConfig
                        # 简化配置以减少超时
                        rag_config = AgenticRAGConfig(
                            enable_task_decomposition=False,  # 禁用任务分解以加快速度
                            enable_self_reflection=False,     # 禁用自反思以加快速度
                            max_retrieval_rounds=1            # 减少检索轮次
                        )
                        rag = AgenticRAG(config=rag_config)
                        rag_result = rag.query(
                            query=user_message,
                            knowledge_base_name=request.knowledge_base_name
                        )
                        
                        # 构建参考信息字符串
                        context_items = []
                        if rag_result.get("sources"):
                            for i, source in enumerate(rag_result.get("sources", [])[:3], 1):
                                context_items.append(f"[参考{i}] {source}")
                        context_str = "\n".join(context_items) if context_items else ""
                        
                        # 保存思考过程供后续发送
                        reasoning_trace = rag_result.get("reasoning_trace", [])
                        query_type = rag_result.get("query_type", "unknown")
                        strategy = rag_result.get("strategy", "hybrid")
                    else:
                        context_str = ""
                        reasoning_trace = []
                        query_type = "unknown"
                        strategy = "hybrid"
                    
                    # 获取当前启用的提示词模板
                    from app.core.prompt_manager import prompt_manager
                    active_template = prompt_manager.get_active_template(db)
                    
                    if active_template:
                        import json
                        template_variables = json.loads(active_template.variables) if active_template.variables else []
                        
                        # 构建变量字典
                        variables = {"requirement": user_message}
                        if "context" in template_variables and context_str:
                            variables["context"] = context_str
                        
                        # 使用模板格式化提示词
                        formatted_result = prompt_manager.format_prompt(
                            db,
                            active_template.name,
                            variables
                        )
                        
                        # 使用格式化后的消息
                        enhanced_messages = [
                            {"role": "system", "content": formatted_result.system},
                            {"role": "user", "content": formatted_result.user}
                        ]
                        chat_params["messages"] = enhanced_messages
                    else:
                        # 没有启用的提示词模板，使用简单逻辑
                        enhanced_messages = messages.copy()
                        if context_str:
                            enhanced_messages[-1]["content"] = (
                                f"参考信息:\n{context_str}\n\n"
                                f"用户问题: {user_message}\n\n"
                                f"请根据参考信息回答用户的问题。"
                            )
                        chat_params["messages"] = enhanced_messages
                    
                    db.close()
                    
                    # 创建自定义客户端，设置更长超时时间
                    import httpx
                    timeout_config = httpx.Timeout(timeout=600.0, connect=10.0)
                    
                    from zhipuai import ZhipuAI
                    if model_config and model_config.api_key:
                        client_kwargs = {"api_key": model_config.api_key, "timeout": timeout_config}
                        if model_config.api_base:
                            client_kwargs["base_url"] = model_config.api_base
                        client = ZhipuAI(**client_kwargs)
                    else:
                        from app.config import settings
                        client = ZhipuAI(api_key=settings.zhipuai_api_key, timeout=timeout_config)
                    
                    # 调用API并流式返回
                    response = client.chat.completions.create(**chat_params)
                    
                    async def generate():
                        # 如果有思考过程，先发送思考过程
                        if reasoning_trace:
                            thinking_content = "🤔 **思考过程：**\n\n"
                            
                            # 添加查询路由信息
                            query_type_map = {
                                "FACTUAL": "事实性查询",
                                "CONCEPTUAL": "概念性查询",
                                "PROCEDURAL": "程序性查询",
                                "ANALYTICAL": "分析性查询",
                                "EXPLORATORY": "探索性查询"
                            }
                            
                            if query_type:
                                thinking_content += f"📋 **查询类型：** {query_type_map.get(query_type, query_type)}\n\n"
                            
                            # 添加检索策略
                            strategy_map = {
                                "semantic": "语义检索",
                                "keyword": "关键词检索",
                                "hybrid": "混合检索"
                            }
                            if strategy:
                                thinking_content += f"🔍 **检索策略：** {strategy_map.get(strategy, strategy)}\n\n"
                            
                            # 添加推理轨迹
                            for trace in reasoning_trace:
                                step_name = trace.get("step", "")
                                result = trace.get("result", {})
                                
                                if step_name == "query_routing":
                                    thinking_content += f"🎯 **查询路由：** 分析完成\n\n"
                                elif step_name == "task_decomposition":
                                    subtasks = result.get("subtasks", [])
                                    if subtasks:
                                        thinking_content += f"📝 **任务分解：**\n"
                                        for i, subtask in enumerate(subtasks, 1):
                                            thinking_content += f"  {i}. {subtask.get('task', '')}\n"
                                        thinking_content += "\n"
                                elif step_name == "retrieval":
                                    thinking_content += f"📚 **知识检索：** 检索到 {len(result.get('sources', []))} 条相关内容\n\n"
                            
                            thinking_content += "---\n\n"
                            
                            yield f"data: {json.dumps({'content': thinking_content, 'type': 'thinking'}, ensure_ascii=False)}\n\n"
                        
                        # 发送实际回复内容
                        for chunk in response:
                            if chunk.choices[0].delta.content:
                                content = chunk.choices[0].delta.content
                                yield f"data: {json.dumps({'content': content, 'type': 'response'}, ensure_ascii=False)}\n\n"
                        yield "data: [DONE]\n\n"
                    
                    return StreamingResponse(generate(), media_type="text/event-stream")
                
            finally:
                db.close()
        else:
            # 非流式输出（原有逻辑）
            result = llm_service.chat_with_config(
                messages=messages,
                config_name=request.model_config_name,
                stream=request.stream,
                knowledge_base_name=request.knowledge_base_name
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
