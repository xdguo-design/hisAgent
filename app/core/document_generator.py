"""
文档代码生成服务

根据上传的设计文档生成代码实现。
支持Markdown和Word格式文档。
"""

import os
import uuid
from typing import Dict, Any, Optional
from pathlib import Path

from app.core.llm_service import LLMService
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class DocumentGenerator:
    def __init__(self):
        self.llm_service = LLMService()
        self.agent_name = "his_development_assistant"

    def parse_document(self, file_path: str) -> str:
        """
        解析文档内容

        Args:
            file_path: 文档文件路径

        Returns:
            文档内容文本
        """
        try:
            ext = Path(file_path).suffix.lower()

            if ext == '.md':
                return self._parse_markdown(file_path)
            elif ext in ['.docx', '.doc']:
                return self._parse_word(file_path)
            else:
                raise ValueError(f"不支持的文档格式: {ext}")

        except Exception as e:
            logger.error(f"解析文档失败: {e}")
            raise

    def _parse_markdown(self, file_path: str) -> str:
        """
        解析Markdown文档

        Args:
            file_path: Markdown文件路径

        Returns:
            文档内容
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"成功解析Markdown文档: {file_path}")
            return content
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read()
            logger.info(f"成功解析Markdown文档(GBK编码): {file_path}")
            return content

    def _parse_word(self, file_path: str) -> str:
        """
        解析Word文档

        Args:
            file_path: Word文件路径

        Returns:
            文档内容
        """
        try:
            from docx import Document
            doc = Document(file_path)
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text)
            content = '\n\n'.join(paragraphs)
            logger.info(f"成功解析Word文档: {file_path}")
            return content
        except Exception as e:
            logger.error(f"解析Word文档失败: {e}")
            raise

    def extract_requirements(self, content: str) -> Dict[str, Any]:
        """
        从文档中提取需求信息

        Args:
            content: 文档内容

        Returns:
            需求信息字典
        """
        try:
            prompt = f"""
请分析以下设计文档，提取关键需求信息。请以JSON格式返回，包含以下字段：

- title: 文档标题
- description: 功能描述
- requirements: 功能需求列表
- technical_requirements: 技术要求列表
- api_requirements: API接口需求（如果有）
- database_requirements: 数据库需求（如果有）
- code_suggestions: 建议的代码结构

文档内容：
{content}

请只返回JSON，不要有其他内容。
"""

            messages = [
                {"role": "system", "content": "你是一个专业的需求分析专家，擅长从设计文档中提取需求信息。"},
                {"role": "user", "content": prompt}
            ]

            response = self.llm_service.chat_with_config(messages)
            result = response.get("content", "")

            logger.info(f"成功提取需求信息")
            return {
                "title": "设计文档需求",
                "description": content[:500] + "..." if len(content) > 500 else content,
                "raw_content": content,
                "analysis": result
            }

        except Exception as e:
            logger.error(f"提取需求信息失败: {e}")
            raise

    def generate_code_from_requirements(
        self,
        requirements: Dict[str, Any],
        config_name: Optional[str] = None
    ) -> str:
        """
        根据需求生成代码

        Args:
            requirements: 需求信息
            config_name: 使用的模型配置名称

        Returns:
            生成的代码
        """
        try:
            system_prompt = f"""你是一个专业的Java后端开发工程师，专注于HIS医疗系统开发。
你的名字是 {self.agent_name}，所有生成的代码的创建人都是 {self.agent_name}。

请根据需求文档生成完整的、可直接使用的Java代码，并遵循以下规范：
1. JDK版本使用17
2. 使用Spring Boot框架 + Spring Cloud微服务架构
3. 遵循阿里Java开发规范
4. 代码必须包含完整的包声明、导入、类定义、方法实现
5. 代码示例必须使用markdown代码块格式，并指定语言为java
6. 添加必要的注释说明
7. 考虑异常处理和日志记录
8. **不允许使用Lombok**，所有代码必须手动编写getter/setter/构造函数等方法
9. **ORM框架必须使用Spring Data JPA**，不允许使用MyBatis或其他ORM框架
10. **代码结构必须遵循hip-base-cis-diagnose-ds项目架构**（参考知识库文档）：
    - API层（接口定义层）：包含Service接口、DTO对象（NTO新建、ETO编辑、QTO查询、TO通用）
    - FEIGN客户端层：远程调用接口
    - 服务实现层：包含Entity实体、Repository数据访问、ServiceImpl服务实现、Assembler装配器（实体与DTO转换）、Controller控制器
11. 使用雪花算法ID生成器、支持拼音码和五笔码检索、Specification动态查询、缓存策略
12. 定义业务异常枚举、使用BusinessAssert进行业务验证

生成的代码应该包含：
- Entity实体类（使用JPA注解，如有数据库操作）
- Repository接口（继承JpaRepository，支持Specification动态查询）
- Service接口（在API层）和ServiceImpl实现（在服务实现层）
- Assembler装配器（负责Entity与DTO之间的转换）
- Controller控制器（提供REST API）
- DTO类（NTO新建对象、ETO编辑对象、QTO查询对象、TO通用对象）
- 异常处理类和枚举（如有必要）
- Feign客户端接口（如需远程调用）
"""

            user_prompt = f"""
请根据以下需求生成Java代码实现：

需求描述：{requirements.get('description', '')}

需求分析：
{requirements.get('analysis', '')}

原始文档内容：
{requirements.get('raw_content', '')}

请生成完整的、符合规范的Java代码实现。
"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            response = self.llm_service.chat_with_config(messages, config_name=config_name)
            code = response.get("content", "")

            logger.info(f"成功生成代码，创建人: {self.agent_name}")
            return code

        except Exception as e:
            logger.error(f"生成代码失败: {e}")
            raise

    def process_document(
        self,
        file_path: str,
        config_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        处理文档并生成代码

        Args:
            file_path: 文档文件路径
            config_name: 使用的模型配置名称

        Returns:
            处理结果，包含需求和代码
        """
        try:
            logger.info(f"开始处理文档: {file_path}")

            content = self.parse_document(file_path)
            requirements = self.extract_requirements(content)
            code = self.generate_code_from_requirements(requirements, config_name)

            return {
                "success": True,
                "message": "文档处理成功",
                "agent": self.agent_name,
                "data": {
                    "requirements": requirements,
                    "code": code,
                    "file_name": os.path.basename(file_path)
                }
            }

        except Exception as e:
            logger.error(f"处理文档失败: {e}")
            return {
                "success": False,
                "message": f"文档处理失败: {str(e)}",
                "agent": self.agent_name,
                "data": None
            }


document_generator = DocumentGenerator()
