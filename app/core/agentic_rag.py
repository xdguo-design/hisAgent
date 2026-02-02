"""
Agentic RAG 模块

实现智能检索增强生成（Agentic RAG）系统，具有以下特性：
1. 查询路由：智能分析查询类型，选择最佳检索策略
2. 任务分解：将复杂问题拆分为子任务
3. 动态检索：根据查询类型和上下文动态调整检索参数
4. 自反思：评估检索质量，必要时重新检索
5. 工具调用：支持外部工具集成
6. 多步推理：支持复杂的多步骤查询
"""

from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import json
import re
from zhipuai import ZhipuAI
from llama_index.core import VectorStoreIndex

from app.config import settings
from app.models.database import SessionLocal, KnowledgeBase
from app.core.knowledge_base import KnowledgeBaseService
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class QueryType(Enum):
    """
    查询类型枚举
    
    定义系统支持的不同查询类型：
    - FACTUAL: 事实性查询（具体事实、数据）
    - CONCEPTUAL: 概念性查询（定义、原理、理论）
    - PROCEDURAL: 程序性查询（步骤、流程、操作指南）
    - COMPARATIVE: 比较性查询（对比、差异分析）
    - ANALYTICAL: 分析性查询（深入分析、推理）
    - MULTI_HOP: 多跳查询（需要多次检索的复杂问题）
    - AMBIGUOUS: 模糊查询（需要澄清的问题）
    """
    FACTUAL = "factual"
    CONCEPTUAL = "conceptual"
    PROCEDURAL = "procedural"
    COMPARATIVE = "comparative"
    ANALYTICAL = "analytical"
    MULTI_HOP = "multi_hop"
    AMBIGUOUS = "ambiguous"


class RetrievalStrategy(Enum):
    """
    检索策略枚举
    
    定义不同的检索策略：
    - PRECISE: 精确检索（高相似度阈值，少结果）
    - BROAD: 广泛检索（低相似度阈值，多结果）
    - HYBRID: 混合检索（向量+关键词）
    - SEMANTIC: 语义检索（侧重语义理解）
    - KEYWORD: 关键词检索（侧重精确匹配）
    - MULTI_STAGE: 多阶段检索（粗检+精排）
    """
    PRECISE = "precise"
    BROAD = "broad"
    HYBRID = "hybrid"
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    MULTI_STAGE = "multi_stage"


class AgenticRAGConfig:
    """
    Agentic RAG 配置类
    
    定义 Agent 的各种参数和阈值
    """
    
    def __init__(
        self,
        max_retrieval_rounds: int = 3,
        quality_threshold: float = 0.6,
        enable_task_decomposition: bool = True,
        enable_self_reflection: bool = True,
        enable_tool_use: bool = True,
        default_temperature: float = 0.3,
        reasoning_temperature: float = 0.7
    ):
        self.max_retrieval_rounds = max_retrieval_rounds
        self.quality_threshold = quality_threshold
        self.enable_task_decomposition = enable_task_decomposition
        self.enable_self_reflection = enable_self_reflection
        self.enable_tool_use = enable_tool_use
        self.default_temperature = default_temperature
        self.reasoning_temperature = reasoning_temperature


class QueryRouter:
    """
    查询路由器
    
    使用 LLM 分析用户查询，确定查询类型和最佳检索策略
    """
    
    def __init__(self, api_key: str):
        """
        初始化查询路由器
        
        Args:
            api_key: 智谱AI API密钥
        """
        self.client = ZhipuAI(api_key=api_key)
        self.router_prompt = self._build_router_prompt()
    
    def _build_router_prompt(self) -> str:
        """
        构建查询路由提示词
        
        Returns:
            路由器系统提示词
        """
        return """你是一个查询路由专家，负责分析用户查询并确定最佳检索策略。

查询类型分类：
1. factual - 事实性查询：询问具体事实、数据、时间等
   例："HIS系统是什么时候发布的？"
   
2. conceptual - 概念性查询：询问定义、原理、概念解释
   例："什么是RAG技术？"
   
3. procedural - 程序性查询：询问步骤、流程、操作方法
   例："如何使用HIS系统进行挂号？"
   
4. comparative - 比较性查询：对比两个或多个事物
   例："HIS系统和EMR系统有什么区别？"
   
5. analytical - 分析性查询：需要深入分析和推理
   例："分析HIS系统的优缺点"
   
6. multi_hop - 多跳查询：需要多次检索才能回答
   例："HIS系统的开发者是谁，他还开发了哪些其他系统？"
   
7. ambiguous - 模糊查询：问题不够明确，需要澄清
   例："那个系统怎么用？"

检索策略选择：
- factual → precise（精确检索，高相似度阈值0.8，top_k=3）
- conceptual → semantic（语义检索，中等阈值0.7，top_k=5）
- procedural → broad（广泛检索，低阈值0.6，top_k=7）
- comparative → hybrid（混合检索，阈值0.7，top_k=5）
- analytical → multi_stage（多阶段检索，初检top_k=10，精排top_k=5）
- multi_hop → multi_stage（多阶段检索，每轮top_k=5）
- ambiguous → 需要澄清问题

请以JSON格式返回分析结果：
{
    "query_type": "查询类型",
    "strategy": "检索策略",
    "confidence": 0.0-1.0,
    "need_clarification": false,
    "clarification_question": "如需澄清的问题"
}"""
    
    def route(self, query: str) -> Dict[str, Any]:
        """
        路由查询
        
        Args:
            query: 用户查询文本
        
        Returns:
            路由结果字典，包含查询类型、策略、置信度等
        """
        try:
            response = self.client.chat.completions.create(
                model="glm-4-flash",
                messages=[
                    {"role": "system", "content": self.router_prompt},
                    {"role": "user", "content": f"请分析以下查询：\n{query}"}
                ],
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content
            
            # 提取JSON
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                logger.info(f"查询路由结果: {result}")
                return result
            else:
                logger.warning(f"无法解析路由结果，使用默认策略: {result_text}")
                return self._get_default_route()
        
        except Exception as e:
            logger.error(f"查询路由失败: {e}，使用默认策略")
            return self._get_default_route()
    
    def _get_default_route(self) -> Dict[str, Any]:
        """
        获取默认路由配置
        
        Returns:
            默认路由结果
        """
        return {
            "query_type": "conceptual",
            "strategy": "semantic",
            "confidence": 0.5,
            "need_clarification": False
        }


class TaskDecomposer:
    """
    任务分解器
    
    将复杂查询拆分为多个子任务
    """
    
    def __init__(self, api_key: str):
        """
        初始化任务分解器
        
        Args:
            api_key: 智谱AI API密钥
        """
        self.client = ZhipuAI(api_key=api_key)
        self.decompose_prompt = self._build_decompose_prompt()
    
    def _build_decompose_prompt(self) -> str:
        """
        构建任务分解提示词
        
        Returns:
            分解器系统提示词
        """
        return """你是一个任务分解专家，负责将复杂查询拆分为可独立执行的子任务。

分解原则：
1. 每个子任务应该可以独立完成
2. 子任务之间应该有逻辑顺序
3. 子任务数量不宜过多（2-5个）
4. 明确每个子任务的目标

请以JSON格式返回分解结果：
{
    "subtasks": [
        {
            "id": 1,
            "task": "子任务描述",
            "dependencies": [],
            "priority": "high/medium/low"
        }
    ],
    "execution_order": "sequential/parallel",
    "integration_method": "concatenate/synthesize/compare"
}

execution_order说明：
- sequential: 顺序执行（后续任务依赖前序结果）
- parallel: 并行执行（任务之间无依赖）

integration_method说明：
- concatenate: 直接拼接所有子任务结果
- synthesize: 综合所有子任务结果生成新答案
- compare: 对比所有子任务结果进行分析"""
    
    def decompose(self, query: str) -> Dict[str, Any]:
        """
        分解查询任务
        
        Args:
            query: 用户查询文本
        
        Returns:
            分解结果字典，包含子任务列表、执行顺序等
        """
        try:
            response = self.client.chat.completions.create(
                model="glm-4-flash",
                messages=[
                    {"role": "system", "content": self.decompose_prompt},
                    {"role": "user", "content": f"请分解以下查询：\n{query}"}
                ],
                temperature=0.3
            )
            
            result_text = response.choices[0].message.content
            
            # 提取JSON
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                logger.info(f"任务分解结果: {len(result.get('subtasks', []))} 个子任务")
                return result
            else:
                logger.warning("无法解析分解结果，返回单任务")
                return self._get_single_task(query)
        
        except Exception as e:
            logger.error(f"任务分解失败: {e}，返回单任务")
            return self._get_single_task(query)
    
    def _get_single_task(self, query: str) -> Dict[str, Any]:
        """
        获取单任务配置
        
        Args:
            query: 原始查询
        
        Returns:
            单任务分解结果
        """
        return {
            "subtasks": [
                {
                    "id": 1,
                    "task": query,
                    "dependencies": [],
                    "priority": "high"
                }
            ],
            "execution_order": "sequential",
            "integration_method": "concatenate"
        }


class SelfReflection:
    """
    自反思模块
    
    评估检索结果质量，决定是否需要重新检索
    """
    
    def __init__(self, api_key: str, threshold: float = 0.6):
        """
        初始化自反思模块
        
        Args:
            api_key: 智谱AI API密钥
            threshold: 质量阈值
        """
        self.client = ZhipuAI(api_key=api_key)
        self.threshold = threshold
        self.reflection_prompt = self._build_reflection_prompt()
    
    def _build_reflection_prompt(self) -> str:
        """
        构建自反思提示词
        
        Returns:
            反思系统提示词
        """
        return """你是一个结果质量评估专家，负责评估检索结果的质量。

评估维度：
1. 相关性：检索结果是否与查询相关
2. 完整性：检索结果是否足够回答查询
3. 准确性：检索结果是否准确可靠
4. 充分性：检索结果的数量是否充足

请以JSON格式返回评估结果：
{
    "quality_score": 0.0-1.0,
    "is_satisfactory": true/false,
    "missing_info": ["缺失的关键信息"],
    "suggestions": ["改进建议"],
    "need_retrieval": true/false,
    "new_query": "如需重新检索，建议的新查询"
}"""
    
    def evaluate(
        self,
        query: str,
        context: str,
        answer: str,
        sources: List[str]
    ) -> Dict[str, Any]:
        """
        评估检索结果质量
        
        Args:
            query: 原始查询
            context: 检索到的上下文
            answer: 生成的答案
            sources: 检索来源列表
        
        Returns:
            评估结果字典
        """
        try:
            evaluation_input = f"""
原始查询：{query}

检索上下文：
{context}

生成的答案：
{answer}

检索来源：{', '.join(sources)}

请评估上述检索结果的质量。"""
            
            response = self.client.chat.completions.create(
                model="glm-4-flash",
                messages=[
                    {"role": "system", "content": self.reflection_prompt},
                    {"role": "user", "content": evaluation_input}
                ],
                temperature=0.2
            )
            
            result_text = response.choices[0].message.content
            
            # 提取JSON
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                logger.info(f"质量评估得分: {result.get('quality_score', 0)}")
                return result
            else:
                return self._get_default_evaluation()
        
        except Exception as e:
            logger.error(f"质量评估失败: {e}，使用默认评估")
            return self._get_default_evaluation()
    
    def _get_default_evaluation(self) -> Dict[str, Any]:
        """
        获取默认评估结果
        
        Returns:
            默认评估结果
        """
        return {
            "quality_score": 0.7,
            "is_satisfactory": True,
            "missing_info": [],
            "suggestions": [],
            "need_retrieval": False,
            "new_query": None
        }


class AgenticRAG:
    """
    Agentic RAG 主类
    
    整合查询路由、任务分解、动态检索、自反思等功能，
    实现智能检索增强生成系统
    """
    
    def __init__(
        self,
        config: Optional[AgenticRAGConfig] = None,
        knowledge_base_service: Optional[KnowledgeBaseService] = None
    ):
        """
        初始化 Agentic RAG 系统
        
        Args:
            config: Agentic RAG配置
            knowledge_base_service: 知识库服务实例
        """
        self.config = config or AgenticRAGConfig()
        self.kb_service = knowledge_base_service or KnowledgeBaseService()
        
        # 获取API密钥
        api_key = self._get_api_key()
        
        # 初始化各个模块
        self.router = QueryRouter(api_key)
        self.decomposer = TaskDecomposer(api_key)
        self.reflection = SelfReflection(api_key, self.config.quality_threshold)
        self.client = ZhipuAI(api_key=api_key)
        
        logger.info("Agentic RAG 系统初始化完成")
    
    def _get_api_key(self) -> str:
        """
        获取API密钥
        
        Returns:
            API密钥字符串
        """
        try:
            db = SessionLocal()
            from app.models.database import ModelConfig
            model_config = db.query(ModelConfig).filter(
                ModelConfig.is_default == True,
                ModelConfig.is_active == True
            ).first()
            
            if model_config and model_config.api_key:
                return model_config.api_key
            else:
                return settings.zhipuai_api_key
        except Exception as e:
            logger.error(f"获取API密钥失败: {e}，使用配置文件密钥")
            return settings.zhipuai_api_key
        finally:
            if 'db' in locals():
                db.close()
    
    def query(
        self,
        query: str,
        knowledge_base_name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行 Agentic RAG 查询
        
        Args:
            query: 用户查询文本
            knowledge_base_name: 知识库名称
            **kwargs: 额外参数（可覆盖默认配置）
        
        Returns:
            查询结果字典，包含：
            {
                "answer": str,           # 生成的答案
                "sources": List[str],    # 检索来源
                "reasoning_trace": List[Dict],  # 推理轨迹
                "quality_score": float,  # 质量得分
                "query_type": str,       # 查询类型
                "strategy": str          # 使用的检索策略
            }
        """
        reasoning_trace = []
        
        try:
            # 1. 查询路由
            logger.info(f"开始 Agentic RAG 查询: {query}")
            route_result = self.router.route(query)
            reasoning_trace.append({
                "step": "query_routing",
                "result": route_result
            })
            
            # 2. 检查是否需要澄清
            if route_result.get("need_clarification", False):
                return {
                    "answer": f"抱歉，您的问题不够明确。{route_result.get('clarification_question', '')}",
                    "sources": [],
                    "reasoning_trace": reasoning_trace,
                    "quality_score": 0.0,
                    "query_type": route_result["query_type"],
                    "strategy": route_result["strategy"],
                    "need_clarification": True
                }
            
            # 3. 任务分解（如果启用）
            if self.config.enable_task_decomposition:
                decompose_result = self.decomposer.decompose(query)
                reasoning_trace.append({
                    "step": "task_decomposition",
                    "result": decompose_result
                })
            else:
                decompose_result = {
                    "subtasks": [{"id": 1, "task": query, "dependencies": [], "priority": "high"}],
                    "execution_order": "sequential",
                    "integration_method": "concatenate"
                }
            
            # 4. 执行子任务
            subtask_results = []
            all_sources = []
            
            for subtask in decompose_result.get("subtasks", []):
                subtask_query = subtask["task"]
                
                # 获取检索策略
                strategy = RetrievalStrategy(route_result.get("strategy", "hybrid"))
                
                # 执行检索
                subtask_result = self._execute_retrieval(
                    subtask_query,
                    knowledge_base_name,
                    strategy,
                    route_result["query_type"]
                )
                
                subtask_results.append(subtask_result)
                all_sources.extend(subtask_result.get("sources", []))
            
            # 5. 整合子任务结果
            integration_method = decompose_result.get("integration_method", "concatenate")
            final_answer = self._integrate_results(
                query,
                subtask_results,
                integration_method
            )
            
            # 6. 自反思（如果启用）
            if self.config.enable_self_reflection:
                context = "\n\n".join([r.get("context", "") for r in subtask_results])
                reflection_result = self.reflection.evaluate(
                    query,
                    context,
                    final_answer,
                    list(set(all_sources))
                )
                reasoning_trace.append({
                    "step": "self_reflection",
                    "result": reflection_result
                })
                
                # 7. 如果质量不满意且需要重新检索
                if (not reflection_result.get("is_satisfactory", True) and 
                    reflection_result.get("need_retrieval", False) and
                    len(reasoning_trace) < self.config.max_retrieval_rounds):
                    
                    new_query = reflection_result.get("new_query", query)
                    logger.info(f"质量不满意，使用新查询重新检索: {new_query}")
                    
                    retry_result = self.query(
                        new_query,
                        knowledge_base_name,
                        **kwargs
                    )
                    
                    reasoning_trace.extend(retry_result.get("reasoning_trace", []))
                    final_answer = retry_result["answer"]
                    all_sources = retry_result["sources"]
            
            # 去重来源
            unique_sources = list(dict.fromkeys(all_sources))
            
            logger.info(f"Agentic RAG 查询完成，质量得分: {reflection_result.get('quality_score', 0.7)}")
            
            return {
                "answer": final_answer,
                "sources": unique_sources,
                "reasoning_trace": reasoning_trace,
                "quality_score": reflection_result.get("quality_score", 0.7),
                "query_type": route_result["query_type"],
                "strategy": route_result["strategy"]
            }
        
        except Exception as e:
            logger.error(f"Agentic RAG 查询失败: {e}", exc_info=True)
            raise
    
    def _execute_retrieval(
        self,
        query: str,
        knowledge_base_name: str,
        strategy: RetrievalStrategy,
        query_type: str
    ) -> Dict[str, Any]:
        """
        执行检索
        
        Args:
            query: 查询文本
            knowledge_base_name: 知识库名称
            strategy: 检索策略
            query_type: 查询类型
        
        Returns:
            检索结果字典
        """
        # 根据策略调整检索参数
        params = self._get_retrieval_params(strategy, query_type)
        
        # 执行检索
        result = self.kb_service.query(
            index_name=knowledge_base_name,
            query=query,
            **params
        )
        
        # 提取上下文
        context = self._extract_context(result)
        
        return {
            "answer": result.answer,
            "sources": result.sources,
            "similarity_scores": result.similarity_scores,
            "context": context,
            "strategy": strategy.value,
            "params": params
        }
    
    def _get_retrieval_params(
        self,
        strategy: RetrievalStrategy,
        query_type: str
    ) -> Dict[str, Any]:
        """
        根据策略获取检索参数
        
        Args:
            strategy: 检索策略
            query_type: 查询类型
        
        Returns:
            检索参数字典
        """
        params = {}
        
        if strategy == RetrievalStrategy.PRECISE:
            params = {
                "top_k": 3,
                "similarity_threshold": 0.8
            }
        elif strategy == RetrievalStrategy.BROAD:
            params = {
                "top_k": 10,
                "similarity_threshold": 0.5
            }
        elif strategy == RetrievalStrategy.HYBRID:
            params = {
                "top_k": 5,
                "similarity_threshold": 0.7
            }
        elif strategy == RetrievalStrategy.SEMANTIC:
            params = {
                "top_k": 5,
                "similarity_threshold": 0.7
            }
        elif strategy == RetrievalStrategy.MULTI_STAGE:
            params = {
                "top_k": 10,
                "similarity_threshold": 0.6
            }
        else:
            params = {
                "top_k": settings.default_top_k,
                "similarity_threshold": 0.7
            }
        
        return params
    
    def _extract_context(self, result) -> str:
        """
        从检索结果中提取上下文
        
        Args:
            result: 检索结果对象
        
        Returns:
            上下文文本
        """
        # 这里可以根据实际结果对象调整
        if hasattr(result, 'source_nodes'):
            contexts = [node.node.text for node in result.source_nodes]
            return "\n\n".join(contexts)
        return ""
    
    def _integrate_results(
        self,
        original_query: str,
        subtask_results: List[Dict[str, Any]],
        integration_method: str
    ) -> str:
        """
        整合子任务结果
        
        Args:
            original_query: 原始查询
            subtask_results: 子任务结果列表
            integration_method: 整合方法
        
        Returns:
            整合后的最终答案
        """
        if integration_method == "concatenate":
            # 直接拼接
            answers = [r.get("answer", "") for r in subtask_results]
            return "\n\n".join(answers)
        
        elif integration_method == "synthesize":
            # 使用LLM综合
            contexts = []
            for i, result in enumerate(subtask_results, 1):
                contexts.append(f"子任务{i}结果：{result.get('answer', '')}")
            
            synthesis_prompt = f"""
原始查询：{original_query}

以下是多个子任务的检索结果：

{chr(10).join(contexts)}

请基于上述子任务结果，综合生成一个完整、连贯的答案。"""
            
            try:
                response = self.client.chat.completions.create(
                    model="glm-4-flash",
                    messages=[
                        {"role": "system", "content": "你是一个信息综合专家，擅长整合多个信息源生成连贯的答案。"},
                        {"role": "user", "content": synthesis_prompt}
                    ],
                    temperature=self.config.default_temperature
                )
                
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"综合答案失败: {e}，使用直接拼接")
                return "\n\n".join([r.get("answer", "") for r in subtask_results])
        
        elif integration_method == "compare":
            # 对比分析
            contexts = []
            for i, result in enumerate(subtask_results, 1):
                contexts.append(f"方案{i}：{result.get('answer', '')}")
            
            compare_prompt = f"""
原始查询：{original_query}

以下是多个对比方案的检索结果：

{chr(10).join(contexts)}

请对比分析上述方案，突出各自的异同点。"""
            
            try:
                response = self.client.chat.completions.create(
                    model="glm-4-flash",
                    messages=[
                        {"role": "system", "content": "你是一个对比分析专家，擅长发现不同方案之间的异同。"},
                        {"role": "user", "content": compare_prompt}
                    ],
                    temperature=self.config.reasoning_temperature
                )
                
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"对比分析失败: {e}，使用直接拼接")
                return "\n\n".join([r.get("answer", "") for r in subtask_results])
        
        else:
            # 默认直接拼接
            return "\n\n".join([r.get("answer", "") for r in subtask_results])


# 全局 Agentic RAG 实例
agentic_rag_service = AgenticRAG()
