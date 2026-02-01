"""
HIS专家系统模块

提供HIS（医院信息系统）领域的专业知识服务。
包含临床业务逻辑、代码审查、流程设计等专业功能。
"""

from typing import Dict, List, Optional
from app.models.database import SessionLocal
from app.models.schemas import (
    HISCodeReviewRequest,
    HISDevelopmentAssistantRequest,
    HISWorkflowDesignRequest,
    HISKnowledgeQARequest,
    ChatResponse
)
from app.core.llm_service import llm_service
from app.core.prompt_manager import prompt_manager
from app.core.knowledge_base import knowledge_base_service
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class HISExpert:
    """
    HIS专家系统类
    
    提供HIS系统开发的专业支持，包括：
    1. 代码审查：HIS代码质量审查
    2. 开发助手：HIS功能开发咨询
    3. 知识问答：HIS专业知识问答
    4. 流程设计：临床业务流程设计
    5. 数据库设计：HIS数据库设计咨询
    6. API设计：HIS接口设计咨询
    """
    
    def __init__(self):
        """
        初始化HIS专家系统
        """
        logger.info("HIS专家系统初始化成功")
    
    def code_review(
        self,
        request: HISCodeReviewRequest,
        model_config_name: Optional[str] = None
    ) -> ChatResponse:
        """
        HIS代码审查
        
        对HIS系统代码进行专业审查，包括代码质量、业务逻辑、安全性等方面。
        
        Args:
            request: 代码审查请求，包含代码路径和内容
            model_config_name: 使用的模型配置名称（可选）
        
        Returns:
            审查结果响应
        
        Examples:
            >>> expert = HISExpert()
            >>> request = HISCodeReviewRequest(
            ...     code_path="src/medical/OrderService.java",
            ...     code_content="public class OrderService { ... }"
            ... )
            >>> result = expert.code_review(request)
            >>> print(result.content)
        """
        db = SessionLocal()
        try:
            # 获取提示词
            formatted_prompt = prompt_manager.format_prompt(
                db,
                "his_code_review",
                {
                    "code_path": request.code_path,
                    "code_content": request.code_content
                }
            )
            
            # 构建消息列表
            messages = [
                {"role": "system", "content": formatted_prompt.system},
                {"role": "user", "content": formatted_prompt.user}
            ]
            
            # 调用LLM
            result = llm_service.chat_with_config(
                messages=messages,
                config_name=model_config_name,
                stream=False
            )
            
            logger.info(f"代码审查完成: {request.code_path}")
            
            return ChatResponse(
                content=result["content"],
                model=result["model"],
                usage=result["usage"]
            )
            
        finally:
            db.close()
    
    def development_assistant(
        self,
        request: HISDevelopmentAssistantRequest,
        model_config_name: Optional[str] = None
    ) -> ChatResponse:
        """
        HIS开发助手
        
        为HIS系统开发提供专业的技术咨询和方案设计。
        
        Args:
            request: 开发助手请求，包含需求和背景信息
            model_config_name: 使用的模型配置名称（可选）
        
        Returns:
            开发方案响应
        
        Examples:
            >>> expert = HISExpert()
            >>> request = HISDevelopmentAssistantRequest(
            ...     requirement="实现门诊挂号功能",
            ...     context="需要支持医保结算"
            ... )
            >>> result = expert.development_assistant(request)
            >>> print(result.content)
        """
        db = SessionLocal()
        try:
            # 获取提示词
            formatted_prompt = prompt_manager.format_prompt(
                db,
                "his_development_assistant",
                {
                    "requirement": request.requirement,
                    "context": request.context
                }
            )
            
            # 构建消息列表
            messages = [
                {"role": "system", "content": formatted_prompt.system},
                {"role": "user", "content": formatted_prompt.user}
            ]
            
            # 调用LLM
            result = llm_service.chat_with_config(
                messages=messages,
                config_name=model_config_name,
                stream=False
            )
            
            logger.info(f"开发助手服务完成: {request.requirement[:50]}...")
            
            return ChatResponse(
                content=result["content"],
                model=result["model"],
                usage=result["usage"]
            )
            
        finally:
            db.close()
    
    def knowledge_qa(
        self,
        request: HISKnowledgeQARequest,
        model_config_name: Optional[str] = None
    ) -> ChatResponse:
        """
        HIS知识问答
        
        回答HIS系统相关的专业问题，可结合知识库进行回答。
        
        Args:
            request: 知识问答请求，包含问题和是否使用知识库的配置
            model_config_name: 使用的模型配置名称（可选）
        
        Returns:
            问答响应
        
        Examples:
            >>> expert = HISExpert()
            >>> request = HISKnowledgeQARequest(
            ...     question="什么是HL7标准？",
            ...     use_knowledge_base=True,
            ...     knowledge_base_name="his_knowledge"
            ... )
            >>> result = expert.knowledge_qa(request)
            >>> print(result.content)
        """
        db = SessionLocal()
        try:
            context = ""
            
            # 如果需要使用知识库
            if request.use_knowledge_base and request.knowledge_base_name:
                try:
                    kb_result = knowledge_base_service.query(
                        index_name=request.knowledge_base_name,
                        query=request.question,
                        top_k=3
                    )
                    context = f"\n\n参考信息：\n{kb_result.answer}"
                    logger.info(f"从知识库检索到 {len(kb_result.sources)} 条相关文档")
                except Exception as e:
                    logger.warning(f"知识库查询失败: {e}")
            
            # 获取提示词
            formatted_prompt = prompt_manager.format_prompt(
                db,
                "his_knowledge_qa",
                {"question": request.question}
            )
            
            # 构建消息列表
            user_content = formatted_prompt.user + context
            messages = [
                {"role": "system", "content": formatted_prompt.system},
                {"role": "user", "content": user_content}
            ]
            
            # 调用LLM
            result = llm_service.chat_with_config(
                messages=messages,
                config_name=model_config_name,
                stream=False
            )
            
            logger.info(f"知识问答完成: {request.question[:50]}...")
            
            return ChatResponse(
                content=result["content"],
                model=result["model"],
                usage=result["usage"]
            )
            
        finally:
            db.close()
    
    def workflow_design(
        self,
        request: HISWorkflowDesignRequest,
        model_config_name: Optional[str] = None
    ) -> ChatResponse:
        """
        HIS临床流程设计
        
        为医院临床业务流程设计提供专业咨询。
        
        Args:
            request: 流程设计请求，包含需求和科室信息
            model_config_name: 使用的模型配置名称（可选）
        
        Returns:
            流程设计方案响应
        
        Examples:
            >>> expert = HISExpert()
            >>> request = HISWorkflowDesignRequest(
            ...     workflow_requirement="门诊处方流程",
            ...     department="药房"
            ... )
            >>> result = expert.workflow_design(request)
            >>> print(result.content)
        """
        db = SessionLocal()
        try:
            # 获取提示词
            formatted_prompt = prompt_manager.format_prompt(
                db,
                "his_clinical_workflow_design",
                {
                    "workflow_requirement": request.workflow_requirement,
                    "department": request.department
                }
            )
            
            # 构建消息列表
            messages = [
                {"role": "system", "content": formatted_prompt.system},
                {"role": "user", "content": formatted_prompt.user}
            ]
            
            # 调用LLM
            result = llm_service.chat_with_config(
                messages=messages,
                config_name=model_config_name,
                stream=False
            )
            
            logger.info(f"流程设计完成: {request.department} - {request.workflow_requirement[:50]}...")
            
            return ChatResponse(
                content=result["content"],
                model=result["model"],
                usage=result["usage"]
            )
            
        finally:
            db.close()
    
    def database_design(
        self,
        db_requirement: str,
        business_context: str,
        model_config_name: Optional[str] = None
    ) -> ChatResponse:
        """
        HIS数据库设计
        
        为HIS系统数据库设计提供专业咨询。
        
        Args:
            db_requirement: 数据库设计需求
            business_context: 业务场景描述
            model_config_name: 使用的模型配置名称（可选）
        
        Returns:
            数据库设计方案响应
        """
        db = SessionLocal()
        try:
            # 获取提示词
            formatted_prompt = prompt_manager.format_prompt(
                db,
                "his_database_design",
                {
                    "db_requirement": db_requirement,
                    "business_context": business_context
                }
            )
            
            # 构建消息列表
            messages = [
                {"role": "system", "content": formatted_prompt.system},
                {"role": "user", "content": formatted_prompt.user}
            ]
            
            # 调用LLM
            result = llm_service.chat_with_config(
                messages=messages,
                config_name=model_config_name,
                stream=False
            )
            
            logger.info(f"数据库设计完成: {db_requirement[:50]}...")
            
            return ChatResponse(
                content=result["content"],
                model=result["model"],
                usage=result["usage"]
            )
            
        finally:
            db.close()
    
    def api_design(
        self,
        api_requirement: str,
        business_context: str,
        model_config_name: Optional[str] = None
    ) -> ChatResponse:
        """
        HIS API设计
        
        为HIS系统API设计提供专业咨询。
        
        Args:
            api_requirement: API设计需求
            business_context: 业务场景描述
            model_config_name: 使用的模型配置名称（可选）
        
        Returns:
            API设计方案响应
        """
        db = SessionLocal()
        try:
            # 获取提示词
            formatted_prompt = prompt_manager.format_prompt(
                db,
                "his_api_design",
                {
                    "api_requirement": api_requirement,
                    "business_context": business_context
                }
            )
            
            # 构建消息列表
            messages = [
                {"role": "system", "content": formatted_prompt.system},
                {"role": "user", "content": formatted_prompt.user}
            ]
            
            # 调用LLM
            result = llm_service.chat_with_config(
                messages=messages,
                config_name=model_config_name,
                stream=False
            )
            
            logger.info(f"API设计完成: {api_requirement[:50]}...")
            
            return ChatResponse(
                content=result["content"],
                model=result["model"],
                usage=result["usage"]
            )
            
        finally:
            db.close()
    
    def get_his_categories(self) -> List[str]:
        """
        获取HIS业务分类
        
        Returns:
            业务分类列表
        """
        return [
            "outpatient",
            "inpatient",
            "pharmacy",
            "laboratory",
            "radiology",
            "surgery",
            "emergency",
            "medical_record",
            "nursing",
            "charging",
            "insurance",
            "material",
            "equipment",
            "quality_control",
            "statistics",
            "integration"
        ]
    
    def get_departments(self) -> Dict[str, List[str]]:
        """
        获取医院科室分类
        
        Returns:
            科室分类字典，key为科室类型，value为科室列表
        """
        return {
            "临床科室": [
                "内科", "外科", "妇产科", "儿科", "眼科", "耳鼻喉科",
                "口腔科", "皮肤科", "精神科", "传染科", "肿瘤科", "急诊科"
            ],
            "医技科室": [
                "检验科", "放射科", "超声科", "病理科", "核医学科",
                "药剂科", "输血科", "营养科", "康复科"
            ],
            "行政科室": [
                "医务科", "护理部", "门诊部", "住院部", "感染管理科",
                "质控科", "信息科", "设备科", "总务科"
            ]
        }
    
    def get_his_modules(self) -> List[str]:
        """
        获取HIS系统模块列表
        
        Returns:
            系统模块列表
        """
        return [
            "门诊挂号系统",
            "门诊收费系统",
            "门诊药房系统",
            "门诊医生工作站",
            "住院登记系统",
            "住院护士工作站",
            "住院医生工作站",
            "住院药房系统",
            "医嘱管理系统",
            "电子病历系统",
            "检验系统(LIS)",
            "影像系统(PACS)",
            "手术麻醉系统",
            "血液透析系统",
            "体检系统",
            "健康档案系统",
            "排班管理系统",
            "物资管理系统",
            "设备管理系统",
            "财务核算系统",
            "医保结算系统",
            "院长决策支持系统"
        ]
    
    def get_his_standards(self) -> List[str]:
        """
        获取HIS相关标准和规范
        
        Returns:
            标准和规范列表
        """
        return [
            "HL7 (Health Level 7)",
            "DICOM (医学影像标准)",
            "ICD-10 (疾病分类编码)",
            "ICD-9-CM (手术操作编码)",
            "CPT (医疗服务术语)",
            "LOINC (检验观察标识符)",
            "SNOMED CT (系统医学临床术语集)",
            "国家卫健委《医院信息互联互通标准化成熟度测评》",
            "国家卫健委《电子病历应用水平分级评价》",
            "国家医保局《医疗保障信息平台技术规范》",
            "WS/T 482-2016 《卫生信息共享文档规范》",
            "WS/T 445-2014 《电子病历基本数据集》"
        ]


# 全局HIS专家系统实例
his_expert = HISExpert()
