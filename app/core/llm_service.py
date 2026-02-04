"""
LLM服务模块

封装智谱AI的调用逻辑，提供统一的对话接口。
支持普通对话和流式对话两种模式。
"""

from zhipuai import ZhipuAI
from typing import List, Dict, Optional, AsyncGenerator
from app.config import settings
from app.models.database import ModelConfig
from app.models.schemas import ChatRequest, ChatResponse
from app.utils.logger import setup_logger
from app.core.agentic_rag import AgenticRAG, AgenticRAGConfig
import httpx

logger = setup_logger(__name__)


class LLMService:
    """
    LLM服务类
    
    封装智谱AI的API调用，提供以下功能：
    1. 普通对话：一次性返回完整回复
    2. 流式对话：逐块返回回复内容
    3. 模型配置管理：支持从数据库加载模型参数
    
    Attributes:
        client: 智谱AI客户端实例
        default_model: 默认使用的模型名称
    """
    
    # 智谱AI支持的模型列表
    AVAILABLE_MODELS = {
        # GLM系列模型
        "glm-4": "智谱AI GLM-4模型，通用能力强",
        "glm-4-plus": "智谱AI GLM-4 Plus模型，性能更强",
        "glm-4.7": "智谱AI GLM-4.7模型，最新版本",
        "glm-4-7b": "智谱AI GLM-4.7B模型，轻量级版本",
        "glm-4-9b": "智谱AI GLM-4.9B模型，中等规模",
        "glm-4-20b": "智谱AI GLM-4.20B模型，大规模版本",
        "glm-4-32b": "智谱AI GLM-4.32B模型，超大规模",
        "glm-4-128k": "智谱AI GLM-4 128K上下文模型",
        "glm-4-0520": "智谱AI GLM-4-0520版本",
        "glm-4-air": "智谱AI GLM-4 Air模型，轻量高效",
        "glm-4-airx": "智谱AI GLM-4 AirX模型，极速响应",
        "glm-4-flash": "智谱AI GLM-4 Flash模型，超快响应",
        "glm-4-long": "智谱AI GLM-4 Long模型，长上下文",
        "glm-3-turbo": "智谱AI GLM-3 Turbo模型，速度快",
        "glm-3-pro": "智谱AI GLM-3 Pro模型，专业版",
        "glm-4v": "智谱AI GLM-4v模型，支持多模态",
        "glm-4v-plus": "智谱AI GLM-4v Plus模型，多模态增强版",
        
        # OpenAI系列模型（兼容接口）
        "gpt-3.5-turbo": "OpenAI GPT-3.5 Turbo模型",
        "gpt-3.5-turbo-16k": "OpenAI GPT-3.5 Turbo 16K上下文",
        "gpt-4": "OpenAI GPT-4模型",
        "gpt-4-turbo": "OpenAI GPT-4 Turbo模型",
        "gpt-4-turbo-preview": "OpenAI GPT-4 Turbo预览版",
        "gpt-4o": "OpenAI GPT-4o模型，多模态",
        "gpt-4o-mini": "OpenAI GPT-4o Mini模型，轻量版",
        "gpt-4-vision-preview": "OpenAI GPT-4 Vision预览版",
        
        # Claude系列模型（兼容接口）
        "claude-3-opus": "Anthropic Claude-3 Opus模型，最强版本",
        "claude-3-sonnet": "Anthropic Claude-3 Sonnet模型，平衡版本",
        "claude-3-haiku": "Anthropic Claude-3 Haiku模型，快速版本",
        "claude-3-5-sonnet": "Anthropic Claude-3.5 Sonnet模型，增强版",
        
        # 其他主流模型（兼容接口）
        "qwen-turbo": "阿里云通义千问Turbo模型",
        "qwen-plus": "阿里云通义千问Plus模型",
        "qwen-max": "阿里云通义千问Max模型",
        "moonshot-v1-8k": "月之暗面Moonshot 8K模型",
        "moonshot-v1-32k": "月之暗面Moonshot 32K模型",
        "moonshot-v1-128k": "月之暗面Moonshot 128K模型",
        "deepseek-chat": "深度求索DeepSeek Chat模型",
        "deepseek-coder": "深度求索DeepSeek Coder模型",
        "baichuan2-turbo": "百川Baichuan2 Turbo模型",
        "baichuan2-53b": "百川Baichuan2 53B模型",
        "yi-34b-chat": "零一万物Yi-34B Chat模型",
        "yi-large": "零一万物Yi Large模型",
        "yi-medium": "零一万物Yi Medium模型",
        "yi-spark": "零一万物Yi Spark模型",
        "yi-lightning": "零一万物Yi Lightning模型",
        "hunyuan-lite": "腾讯混元Lite模型",
        "hunyuan-standard": "腾讯混元Standard模型",
        "hunyuan-pro": "腾讯混元Pro模型",
        "bge-large": "BGE Large嵌入模型",
        "text-embedding-ada-002": "OpenAI文本嵌入模型",
        "text-embedding-3-small": "OpenAI文本嵌入3 Small模型",
        "text-embedding-3-large": "OpenAI文本嵌入3 Large模型"
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化LLM服务
        
        Args:
            api_key: 智谱AI API密钥，如果为None则从配置文件读取
        """
        timeout_config = httpx.Timeout(timeout=600.0, connect=10.0)
        self.client = ZhipuAI(api_key=api_key or settings.zhipuai_api_key, timeout=timeout_config)
        self.default_model = "glm-4"
        
        # 初始化 Agentic RAG 实例
        rag_config = AgenticRAGConfig(
            enable_task_decomposition=True,
            enable_self_reflection=True,
            max_retrieval_rounds=2
        )
        self.rag = AgenticRAG(config=rag_config)
        
        logger.info("LLM服务初始化成功")
    
    def get_model_config(self, config_name: Optional[str]) -> Dict[str, any]:
        """
        获取模型配置
        
        从数据库加载指定名称的模型配置，如果未指定则使用数据库中第一个激活的配置。
        
        Args:
            config_name: 模型配置名称
        
        Returns:
            包含模型参数的字典
        """
        from app.models.database import SessionLocal
        
        default_config = {
            "model": self.default_model,
            "temperature": settings.default_temperature,
            "max_tokens": settings.default_max_tokens,
            "top_p": settings.default_top_p,
            "api_key": None,
            "api_base": None
        }
        
        try:
            db = SessionLocal()
            
            if not config_name:
                model_config = db.query(ModelConfig).filter(
                    ModelConfig.is_active == True
                ).first()
                
                if model_config:
                    config = {
                        "model": model_config.model_name,
                        "temperature": model_config.temperature,
                        "max_tokens": model_config.max_tokens,
                        "top_p": model_config.top_p,
                        "api_key": model_config.api_key,
                        "api_base": model_config.api_base
                    }
                    logger.info(f"使用数据库默认模型配置: {model_config.name}")
                    return config
                else:
                    logger.debug("使用默认模型配置")
                    return default_config
            else:
                model_config = db.query(ModelConfig).filter(
                    ModelConfig.name == config_name,
                    ModelConfig.is_active == True
                ).first()
                
                if model_config:
                    config = {
                        "model": model_config.model_name,
                        "temperature": model_config.temperature,
                        "max_tokens": model_config.max_tokens,
                        "top_p": model_config.top_p,
                        "api_key": model_config.api_key,
                        "api_base": model_config.api_base
                    }
                    logger.info(f"使用模型配置: {config_name}")
                    return config
                else:
                    logger.warning(f"未找到模型配置: {config_name}，使用默认配置")
                    return default_config
        except Exception as e:
            logger.error(f"加载模型配置失败: {e}")
            return default_config
        finally:
            db.close()
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        top_p: float = None,
        api_key: str = None,
        api_base: str = None,
        stream: bool = False
    ) -> Dict:
        """
        普通对话接口
        
        发送对话请求并一次性返回完整回复。
        
        Args:
            messages: 消息列表，每条消息包含role和content字段
            model: 模型名称，如果为None则使用默认模型
            temperature: 温度参数，控制输出随机性（0-2）
            max_tokens: 最大生成的token数量
            top_p: Top-p采样参数（0-1）
            stream: 是否使用流式输出
        
        Returns:
            包含回复内容和元数据的字典，格式：
            {
                "content": str,  # AI回复内容
                "model": str,   # 使用的模型
                "usage": {      # Token使用情况
                    "prompt_tokens": int,
                    "completion_tokens": int,
                    "total_tokens": int
                }
            }
        
        Raises:
            Exception: API调用失败时抛出异常
        
        Examples:
            >>> service = LLMService()
            >>> messages = [
            ...     {"role": "user", "content": "你好"}
            ... ]
            >>> response = service.chat(messages)
            >>> print(response["content"])
        """
        try:
            # 使用默认值填充未指定的参数
            model = model or self.default_model
            temperature = temperature if temperature is not None else settings.default_temperature
            max_tokens = max_tokens if max_tokens is not None else settings.default_max_tokens
            top_p = top_p if top_p is not None else settings.default_top_p
            
            logger.debug(f"调用模型: {model}, temperature: {temperature}, max_tokens: {max_tokens}")
            logger.debug(f"使用API密钥: {api_key[:20] if api_key else '使用默认密钥'}...")
            
            # 如果提供了自定义 API 密钥或 API Base，创建新的客户端实例
            client = self.client
            if api_key or api_base:
                client_kwargs = {}
                if api_key:
                    client_kwargs["api_key"] = api_key
                if api_base:
                    client_kwargs["base_url"] = api_base
                client_kwargs["timeout"] = httpx.Timeout(timeout=600.0, connect=10.0)
                client = ZhipuAI(**client_kwargs)
            
            # 调用智谱AI API
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                stream=stream
            )
            
            if stream:
                # 流式输出模式，返回响应对象
                return {"stream": True, "response": response}
            else:
                # 普通模式，返回完整回复
                result = {
                    "content": response.choices[0].message.content,
                    "model": response.model,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                }
                
                logger.info(
                    f"对话完成 - 模型: {result['model']}, "
                    f"Token使用: {result['usage']['total_tokens']}"
                )
                
                return result
                
        except Exception as e:
            logger.error(f"智谱AI API调用失败: {e}")
            raise
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        top_p: float = None
    ) -> AsyncGenerator[str, None]:
        """
        流式对话接口
        
        发送对话请求并逐块返回回复内容，适用于实时显示的场景。
        
        Args:
            messages: 消息列表，每条消息包含role和content字段
            model: 模型名称，如果为None则使用默认模型
            temperature: 温度参数，控制输出随机性（0-2）
            max_tokens: 最大生成的token数量
            top_p: Top-p采样参数（0-1）
        
        Yields:
            AI回复的文本块
        
        Raises:
            Exception: API调用失败时抛出异常
        
        Examples:
            >>> service = LLMService()
            >>> messages = [{"role": "user", "content": "你好"}]
            >>> async for chunk in service.chat_stream(messages):
            ...     print(chunk, end="", flush=True)
        """
        try:
            # 使用默认值填充未指定的参数
            model = model or self.default_model
            temperature = temperature if temperature is not None else settings.default_temperature
            max_tokens = max_tokens if max_tokens is not None else settings.default_max_tokens
            top_p = top_p if top_p is not None else settings.default_top_p
            
            logger.debug(f"流式调用模型: {model}")
            
            # 调用智谱AI流式API
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                stream=True
            )
            
            # 逐块返回内容
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            
            logger.info(f"流式对话完成 - 模型: {model}")
            
        except Exception as e:
            logger.error(f"智谱AI流式API调用失败: {e}")
            raise
    
    def chat_with_config(
        self,
        messages: List[Dict[str, str]],
        config_name: Optional[str] = None,
        stream: bool = False,
        knowledge_base_name: Optional[str] = None
    ) -> Dict:
        """
        使用指定配置进行对话
        
        从数据库加载模型配置并进行对话。如果指定了知识库,将使用RAG增强对话。
        
        Args:
            messages: 消息列表
            config_name: 模型配置名称,如果为None则使用默认配置
            stream: 是否使用流式输出
            knowledge_base_name: 知识库名称,如果指定则使用RAG查询
        
        Returns:
            对话响应结果
        
        Examples:
            >>> service = LLMService()
            >>> messages = [{"role": "user", "content": "你好"}]
            >>> response = service.chat_with_config(messages, "my_config")
            >>> # 使用知识库
            >>> response = service.chat_with_config(messages, knowledge_base_name="my_kb")
        """
        # 如果指定了知识库,使用RAG查询
        if knowledge_base_name:
            try:
                # 提取最后一条用户消息作为查询
                user_message = ""
                for msg in reversed(messages):
                    if msg.get("role") == "user":
                        user_message = msg.get("content", "")
                        break
                
                if not user_message:
                    logger.warning("未找到用户消息,使用普通对话")
                else:
                    logger.info(f"使用知识库 '{knowledge_base_name}' 进行RAG查询")
                    
                    # 使用RAG查询知识库
                    rag_result = self.rag.query(
                        query=user_message,
                        knowledge_base_name=knowledge_base_name
                    )
                    
                    # 构建增强的messages
                    enhanced_messages = messages.copy()
                    
                    # 在最后一条用户消息后添加检索到的上下文
                    context_items = []
                    if rag_result.get("sources"):
                        for i, source in enumerate(rag_result.get("sources", [])[:3], 1):
                            context_items.append(f"[参考{i}] {source}")
                    
                    if context_items:
                        context_str = "\n".join(context_items)
                        enhanced_messages[-1]["content"] = (
                            f"参考信息:\n{context_str}\n\n"
                            f"用户问题: {user_message}\n\n"
                            f"请根据参考信息回答用户的问题。"
                        )
                    
                    # 获取模型配置
                    config = self.get_model_config(config_name)
                    
                    # 使用增强的messages进行对话
                    chat_params = {
                        "messages": enhanced_messages,
                        "model": config["model"],
                        "temperature": config["temperature"],
                        "max_tokens": config["max_tokens"],
                        "top_p": config["top_p"],
                        "stream": stream
                    }
                    
                    if config["api_key"]:
                        chat_params["api_key"] = config["api_key"]
                    
                    if config.get("api_base"):
                        chat_params["api_base"] = config["api_base"]
                    
                    result = self.chat(**chat_params)
                    
                    # 添加RAG相关信息到结果
                    result["sources"] = rag_result.get("sources", [])
                    result["quality_score"] = rag_result.get("quality_score", 0.0)
                    result["query_type"] = rag_result.get("query_type", "")
                    
                    return result
                    
            except Exception as e:
                logger.error(f"RAG查询失败: {e},回退到普通对话")
        
        # 普通对话模式
        config = self.get_model_config(config_name)
        
        # 准备调用参数
        chat_params = {
            "messages": messages,
            "model": config["model"],
            "temperature": config["temperature"],
            "max_tokens": config["max_tokens"],
            "top_p": config["top_p"],
            "stream": stream
        }
        
        # 只有当 API 密钥存在时才传递
        if config["api_key"]:
            chat_params["api_key"] = config["api_key"]
            logger.info(f"使用配置的API密钥: {config['api_key'][:20]}...")
        else:
            logger.info("使用默认API密钥")
        
        # 只有当 API Base 存在时才传递
        if config.get("api_base"):
            chat_params["api_base"] = config["api_base"]
            logger.info(f"使用API Base: {config['api_base']}")
        
        # 使用配置参数进行对话
        return self.chat(**chat_params)
    
    def list_models(self) -> List[Dict[str, str]]:
        """
        列出所有可用模型
        
        Returns:
            模型列表，每个模型包含name和description字段
        """
        return [
            {"name": name, "description": desc}
            for name, desc in self.AVAILABLE_MODELS.items()
        ]
    
    def validate_model(self, model_name: str) -> bool:
        """
        验证模型名称是否有效
        
        Args:
            model_name: 模型名称
        
        Returns:
            如果模型有效返回True，否则返回False
        """
        return model_name in self.AVAILABLE_MODELS


# 全局LLM服务实例，应用启动时初始化
llm_service = LLMService()
