"""
提示词管理模块

提供提示词模板的创建、管理、格式化等功能。
支持变量替换，使提示词可以动态生成。
"""

from typing import Dict, List, Optional
from app.models.database import SessionLocal, PromptTemplate
from app.models.schemas import (
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptFormatResponse
)
from app.utils.logger import setup_logger
from app.utils.helpers import extract_variables_from_template
import json

logger = setup_logger(__name__)


class PromptManager:
    """
    提示词管理器类
    
    提供完整的提示词模板管理功能：
    1. 创建模板：创建新的提示词模板
    2. 查询模板：根据名称或分类查询模板
    3. 更新模板：修改已有的提示词模板
    4. 删除模板：删除不需要的模板
    5. 格式化提示词：使用变量替换生成最终提示词
    6. 初始化默认模板：创建系统预置的提示词模板
    
    Attributes:
        _templates_cache: 模板缓存字典
    """
    
    def __init__(self):
        """
        初始化提示词管理器
        
        创建空的模板缓存。
        """
        self._templates_cache: Dict[str, PromptTemplate] = {}
        logger.info("提示词管理器初始化成功")
    
    def create_template(
        self,
        db,
        template_data: PromptTemplateCreate
    ) -> PromptTemplate:
        """
        创建提示词模板
        
        在数据库中创建新的提示词模板，并更新缓存。
        
        Args:
            db: 数据库会话
            template_data: 提示词模板创建数据
        
        Returns:
            创建的模板对象
        
        Raises:
            Exception: 创建失败时抛出异常
        
        Examples:
            >>> manager = PromptManager()
            >>> from app.models.database import SessionLocal
            >>> db = SessionLocal()
            >>> data = PromptTemplateCreate(
            ...     name="my_template",
            ...     category="development",
            ...     system_prompt="你是一个助手",
            ...     user_prompt_template="帮我{task}"
            ... )
            >>> template = manager.create_template(db, data)
        """
        try:
            # 提取模板变量
            variables = extract_variables_from_template(
                template_data.user_prompt_template
            )
            
            # 创建模板实体
            template = PromptTemplate(
                name=template_data.name,
                category=template_data.category,
                system_prompt=template_data.system_prompt,
                user_prompt_template=template_data.user_prompt_template,
                description=template_data.description,
                variables=json.dumps(variables),
                is_active=template_data.is_active
            )
            
            db.add(template)
            db.commit()
            db.refresh(template)
            
            # 更新缓存
            self._cache_template(template)
            
            logger.info(f"创建提示词模板成功: {template.name}")
            return template
            
        except Exception as e:
            db.rollback()
            logger.error(f"创建提示词模板失败 {template_data.name}: {e}")
            raise
    
    def get_template(
        self,
        db,
        name: str
    ) -> Optional[PromptTemplate]:
        """
        获取提示词模板
        
        根据模板名称查询模板，优先从缓存中读取。
        
        Args:
            db: 数据库会话
            name: 模板名称
        
        Returns:
            模板对象，如果不存在则返回None
        """
        # 先检查缓存
        if name in self._templates_cache:
            return self._templates_cache[name]
        
        # 从数据库查询
        template = db.query(PromptTemplate).filter(
            PromptTemplate.name == name
        ).first()
        
        if template:
            self._cache_template(template)
        
        return template
    
    def get_template_by_id(
        self,
        db,
        template_id: int
    ) -> Optional[PromptTemplate]:
        """
        根据ID获取提示词模板
        
        Args:
            db: 数据库会话
            template_id: 模板ID
        
        Returns:
            模板对象，如果不存在则返回None
        """
        return db.query(PromptTemplate).filter(
            PromptTemplate.id == template_id
        ).first()
    
    def list_templates(
        self,
        db,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[PromptTemplate]:
        """
        列出提示词模板
        
        支持按分类和状态筛选。
        
        Args:
            db: 数据库会话
            category: 分类筛选（可选）
            is_active: 是否启用筛选（可选）
            skip: 跳过的记录数
            limit: 返回的最大记录数
        
        Returns:
            模板列表
        """
        query = db.query(PromptTemplate)
        
        if category:
            query = query.filter(PromptTemplate.category == category)
        
        if is_active is not None:
            query = query.filter(PromptTemplate.is_active == is_active)
        
        return query.order_by(PromptTemplate.name).offset(skip).limit(limit).all()
    
    def update_template(
        self,
        db,
        template_id: int,
        update_data: PromptTemplateUpdate
    ) -> Optional[PromptTemplate]:
        """
        更新提示词模板
        
        Args:
            db: 数据库会话
            template_id: 模板ID
            update_data: 更新数据（所有字段可选）
        
        Returns:
            更新后的模板对象，如果不存在则返回None
        
        Raises:
            Exception: 更新失败时抛出异常
        """
        try:
            template = self.get_template_by_id(db, template_id)
            if not template:
                return None
            
            # 更新字段
            update_dict = update_data.model_dump(exclude_unset=True)
            
            for key, value in update_dict.items():
                if hasattr(template, key):
                    if key == "user_prompt_template":
                        # 重新提取变量
                        variables = extract_variables_from_template(value)
                        template.variables = json.dumps(variables)
                        setattr(template, key, value)
                    elif key == "variables":
                        template.variables = json.dumps(value)
                    else:
                        setattr(template, key, value)
            
            db.commit()
            db.refresh(template)
            
            # 更新缓存
            if template.name in self._templates_cache:
                self._cache_template(template)
            
            logger.info(f"更新提示词模板成功: {template.name}")
            return template
            
        except Exception as e:
            db.rollback()
            logger.error(f"更新提示词模板失败 {template_id}: {e}")
            raise
    
    def delete_template(
        self,
        db,
        template_id: int
    ) -> bool:
        """
        删除提示词模板
        
        Args:
            db: 数据库会话
            template_id: 模板ID
        
        Returns:
            删除成功返回True，失败返回False
        """
        try:
            template = self.get_template_by_id(db, template_id)
            if not template:
                return False
            
            # 从缓存中移除
            if template.name in self._templates_cache:
                del self._templates_cache[template.name]
            
            db.delete(template)
            db.commit()
            
            logger.info(f"删除提示词模板成功: {template.name}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"删除提示词模板失败 {template_id}: {e}")
            return False
    
    def format_prompt(
        self,
        db,
        template_name: str,
        variables: Dict[str, str]
    ) -> PromptFormatResponse:
        """
        格式化提示词
        
        使用提供的变量值替换模板中的占位符，生成最终的提示词。
        
        Args:
            db: 数据库会话
            template_name: 模板名称
            variables: 变量值字典，key为变量名，value为变量值
        
        Returns:
            格式化后的提示词响应，包含system和user两个字段
        
        Raises:
            ValueError: 模板不存在或变量不匹配时抛出
        
        Examples:
            >>> manager = PromptManager()
            >>> from app.models.database import SessionLocal
            >>> db = SessionLocal()
            >>> result = manager.format_prompt(
            ...     db,
            ...     "my_template",
            ...     {"task": "写一个Python函数"}
            ... )
            >>> print(result.system)
            >>> print(result.user)
        """
        template = self.get_template(db, template_name)
        if not template:
            raise ValueError(f"模板不存在: {template_name}")
        
        # 解析模板变量
        template_variables = json.loads(template.variables) if template.variables else []
        
        # 检查必需变量是否提供
        missing_vars = set(template_variables) - set(variables.keys())
        if missing_vars:
            raise ValueError(
                f"缺少必需的变量: {', '.join(missing_vars)}"
            )
        
        # 替换用户提示词中的变量
        user_prompt = template.user_prompt_template
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            if placeholder in user_prompt:
                user_prompt = user_prompt.replace(placeholder, str(value))
        
        return PromptFormatResponse(
            system=template.system_prompt,
            user=user_prompt
        )
    
    def _cache_template(self, template: PromptTemplate):
        """
        缓存模板
        
        将模板对象添加到缓存中。
        
        Args:
            template: 模板对象
        """
        self._templates_cache[template.name] = template
    
    def clear_cache(self):
        """
        清空模板缓存
        
        清空所有缓存的模板，下次访问时会重新从数据库加载。
        """
        self._templates_cache.clear()
        logger.info("模板缓存已清空")
    
    def get_categories(self, db) -> List[str]:
        """
        获取所有模板分类
        
        Args:
            db: 数据库会话
        
        Returns:
            分类列表
        """
        categories = db.query(PromptTemplate.category).distinct().all()
        return [cat[0] for cat in categories]
    
    def initialize_default_templates(self, db):
        """
        初始化默认提示词模板
        
        创建系统预置的HIS开发相关提示词模板。
        如果模板已存在则跳过。
        
        Args:
            db: 数据库会话
        
        Examples:
            >>> manager = PromptManager()
            >>> from app.models.database import SessionLocal
            >>> db = SessionLocal()
            >>> manager.initialize_default_templates(db)
        """
        default_templates = [
            {
                "name": "his_code_review",
                "category": "code_review",
                "system_prompt": "你是一位资深的HIS系统开发专家，精通Java技术栈和医院临床业务流程。请对提供的代码进行专业的代码审查。",
                "user_prompt_template": "请审查以下代码：\n\n代码路径：{code_path}\n\n代码内容：\n{code_content}\n\n请从以下方面进行审查：\n1. 代码质量和规范性\n2. HIS业务逻辑的准确性\n3. 潜在的安全问题\n4. 性能优化建议\n5. 临床业务流程的合规性",
                "description": "HIS代码审查提示词",
                "is_active": False
            },
            {
                "name": "his_development_assistant",
                "category": "development",
                "system_prompt": "你是一位专业的HIS系统开发工程师，精通Java、Spring Boot、MyBatis等技术，并且深入了解医院信息系统的临床业务流程，包括门诊、住院、药房、医嘱管理等。",
                "user_prompt_template": "需求描述：\n{requirement}\n\n背景信息：\n{context}\n\n请提供详细的开发方案，包括：\n1. 技术架构设计\n2. 数据库设计建议\n3. 核心业务逻辑实现\n4. 接口设计\n5. 注意事项（特别是临床业务相关的合规性要求）",
                "description": "HIS开发助手",
                "is_active": True
            },
            {
                "name": "his_knowledge_qa",
                "category": "qa",
                "system_prompt": "你是一位HIS系统领域的专家，精通医院信息系统的各项业务流程和技术实现。请基于你的专业知识回答问题。",
                "user_prompt_template": "问题：{question}\n\n请提供专业、详细的回答。",
                "description": "HIS知识问答",
                "is_active": False
            },
            {
                "name": "his_clinical_workflow_design",
                "category": "workflow",
                "system_prompt": "你是一位资深HIS临床流程设计专家，精通医院各科室的临床业务流程和系统设计规范。",
                "user_prompt_template": "流程设计需求：\n{workflow_requirement}\n\n科室：{department}\n\n请设计详细的临床业务流程，包括：\n1. 业务流程图\n2. 关键业务节点\n3. 数据流转关系\n4. 异常处理机制\n5. 与其他系统的集成点",
                "description": "HIS临床流程设计",
                "is_active": False
            },
            {
                "name": "his_database_design",
                "category": "database",
                "system_prompt": "你是一位HIS系统数据库设计专家，精通关系型数据库设计和医院业务数据建模。",
                "user_prompt_template": "数据库设计需求：\n{db_requirement}\n\n业务场景：{business_context}\n\n请提供：\n1. 表结构设计\n2. 字段说明\n3. 索引设计建议\n4. 数据完整性约束\n5. 性能优化建议",
                "description": "HIS数据库设计",
                "is_active": False
            },
            {
                "name": "his_api_design",
                "category": "api",
                "system_prompt": "你是一位HIS系统API设计专家，精通RESTful API设计规范和医院业务接口设计。",
                "user_prompt_template": "API设计需求：\n{api_requirement}\n\n业务场景：{business_context}\n\n请提供：\n1. 接口设计（URL、请求方法、参数）\n2. 请求/响应数据结构\n3. 错误码定义\n4. 接口文档示例\n5. 安全性考虑",
                "description": "HIS API设计",
                "is_active": False
            }
        ]
        
        created_count = 0
        skipped_count = 0
        
        for template_data in default_templates:
            # 检查是否已存在
            existing = db.query(PromptTemplate).filter(
                PromptTemplate.name == template_data["name"]
            ).first()
            
            if existing:
                logger.debug(f"模板已存在，跳过: {template_data['name']}")
                skipped_count += 1
                continue
            
            # 创建新模板
            data = PromptTemplateCreate(**template_data)
            self.create_template(db, data)
            created_count += 1
        
        logger.info(
            f"默认模板初始化完成 - 创建: {created_count}, 跳过: {skipped_count}"
        )


# 全局提示词管理器实例
prompt_manager = PromptManager()
