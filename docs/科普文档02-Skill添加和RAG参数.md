# Skill添加和RAG参数配置科普文档

## 一、Skill机制概念

### 1.1 什么是Skill

Skill（技能）是Agent执行特定任务的能力模块。通过Skill机制，可以将Agent的能力进行模块化管理和复用。

**Skill的核心特征：**
- **模块化**：每个Skill专注于一个特定任务
- **可配置**：通过Prompt模板定义行为
- **可复用**：多个Agent可以共享同一个Skill
- **可扩展**：支持动态添加和修改

### 1.2 Skill vs 传统函数

| 特性 | 传统函数 | Skill |
|------|----------|-------|
| 输入输出 | 固定参数 | Prompt模板变量 |
| 行为定义 | 硬编码逻辑 | 动态Prompt |
| 可解释性 | 需要阅读代码 | Prompt直接描述 |
| 修改方式 | 重新编码 | 更新模板 |
| 适用场景 | 确定性逻辑 | 推理类任务 |

### 1.3 Skill的应用场景

#### 适合使用Skill的场景
- 代码审查
- 文档生成
- 问答系统
- 翻译任务
- 内容创作

#### 不适合使用Skill的场景
- 简单的数据处理
- 数学计算
- 文件读写
- 数据库查询

## 二、Skill实现机制

### 2.1 Prompt模板系统

#### 基础模板结构

```python
class PromptTemplate:
    """Prompt模板类"""
    
    def __init__(
        self,
        name: str,
        system_prompt: str,
        user_prompt_template: str,
        variables: List[str]
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.user_prompt_template = user_prompt_template
        self.variables = variables
    
    def format(self, **kwargs) -> tuple:
        """格式化Prompt"""
        # 验证必需变量
        missing_vars = set(self.variables) - set(kwargs.keys())
        if missing_vars:
            raise ValueError(f"缺少必需变量: {missing_vars}")
        
        # 替换变量
        user_prompt = self.user_prompt_template
        for key, value in kwargs.items():
            user_prompt = user_prompt.replace(f"{{{key}}}", str(value))
        
        return self.system_prompt, user_prompt
```

#### 使用示例

```python
# 创建代码审查Skill模板
code_review_template = PromptTemplate(
    name="code_review",
    system_prompt="你是一位资深的代码审查专家",
    user_prompt_template="""
    请审查以下代码：
    
    语言：{language}
    代码：
    ```{language}
    {code}
    ```
    
    审查维度：
    {review_dimensions}
    """,
    variables=["language", "code", "review_dimensions"]
)

# 使用模板
system_prompt, user_prompt = code_review_template.format(
    language="Java",
    code="public class Hello { public static void main(String[] args) { System.out.println(\"Hello\"); } }",
    review_dimensions="代码规范性、性能优化、安全性"
)
```

### 2.2 Prompt Manager实现

#### 数据模型

```python
from sqlalchemy import Column, Integer, String, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class PromptTemplateDB(Base):
    """Prompt模板数据库模型"""
    
    __tablename__ = "prompt_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text)
    system_prompt = Column(Text, nullable=False)
    user_prompt_template = Column(Text, nullable=False)
    variables = Column(Text)  # JSON字符串
    is_active = Column(Boolean, default=True)
    category = Column(String(50))  # 技能分类
```

#### Manager核心功能

```python
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import json

class PromptManager:
    """Prompt管理器"""
    
    def __init__(self):
        self.cache: Dict[str, PromptTemplate] = {}
    
    def create_template(
        self,
        db: Session,
        name: str,
        system_prompt: str,
        user_prompt_template: str,
        variables: List[str],
        description: str = None,
        category: str = None
    ) -> PromptTemplateDB:
        """创建新模板"""
        # 检查是否已存在
        existing = db.query(PromptTemplateDB).filter(
            PromptTemplateDB.name == name
        ).first()
        
        if existing:
            raise ValueError(f"模板已存在: {name}")
        
        # 创建模板
        template = PromptTemplateDB(
            name=name,
            description=description,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            variables=json.dumps(variables),
            category=category
        )
        
        db.add(template)
        db.commit()
        db.refresh(template)
        
        # 更新缓存
        self.cache[name] = self._db_to_template(template)
        
        return template
    
    def get_template(
        self,
        db: Session,
        name: str
    ) -> Optional[PromptTemplate]:
        """获取模板"""
        # 先查缓存
        if name in self.cache:
            return self.cache[name]
        
        # 查数据库
        db_template = db.query(PromptTemplateDB).filter(
            PromptTemplateDB.name == name,
            PromptTemplateDB.is_active == True
        ).first()
        
        if not db_template:
            return None
        
        # 转换并缓存
        template = self._db_to_template(db_template)
        self.cache[name] = template
        
        return template
    
    def format_prompt(
        self,
        db: Session,
        template_name: str,
        variables: Dict[str, str]
    ) -> Dict[str, str]:
        """格式化Prompt"""
        template = self.get_template(db, template_name)
        
        if not template:
            raise ValueError(f"模板不存在: {template_name}")
        
        # 验证变量
        required_vars = template.variables
        missing_vars = set(required_vars) - set(variables.keys())
        
        if missing_vars:
            raise ValueError(f"缺少必需变量: {', '.join(missing_vars)}")
        
        # 格式化
        system_prompt = template.system_prompt
        user_prompt = template.user_prompt_template
        
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            user_prompt = user_prompt.replace(placeholder, str(value))
        
        return {
            "system": system_prompt,
            "user": user_prompt
        }
    
    def list_templates(
        self,
        db: Session,
        category: str = None
    ) -> List[PromptTemplateDB]:
        """列出模板"""
        query = db.query(PromptTemplateDB).filter(
            PromptTemplateDB.is_active == True
        )
        
        if category:
            query = query.filter(PromptTemplateDB.category == category)
        
        return query.all()
    
    def delete_template(self, db: Session, name: str) -> bool:
        """删除模板"""
        template = db.query(PromptTemplateDB).filter(
            PromptTemplateDB.name == name
        ).first()
        
        if not template:
            return False
        
        # 软删除
        template.is_active = False
        db.commit()
        
        # 清除缓存
        if name in self.cache:
            del self.cache[name]
        
        return True
    
    def _db_to_template(
        self,
        db_template: PromptTemplateDB
    ) -> PromptTemplate:
        """数据库模型转换为模板对象"""
        variables = json.loads(db_template.variables) if db_template.variables else []
        
        return PromptTemplate(
            name=db_template.name,
            system_prompt=db_template.system_prompt,
            user_prompt_template=db_template.user_prompt_template,
            variables=variables
        )
```

### 2.3 Skill添加流程

#### 步骤1：定义Skill

```python
# 定义代码审查Skill
CODE_REVIEW_SKILL = {
    "name": "code_review",
    "description": "代码审查技能，检查代码规范性、性能、安全性",
    "system_prompt": """你是一位资深的代码审查专家，具有以下能力：
    1. 熟悉多种编程语言的编码规范
    2. 能够识别代码中的性能问题
    3. 能够发现潜在的安全漏洞
    4. 能够提供具体的改进建议
    
    审查时请遵循以下原则：
    - 客观公正，基于事实
    - 优先指出严重问题
    - 提供可执行的改进建议
    - 给出代码示例（如有必要）""",
    
    "user_prompt_template": """请审查以下代码：
    
    编程语言：{language}
    代码内容：
    ```{language}
    {code}
    ```
    
    审查维度：{review_dimensions}
    
    请按照以下格式输出：
    ## 审查结果
    
    ### 严重问题（必须修复）
    1. 问题描述
       - 位置：代码行号
       - 问题类型：[规范性/性能/安全性/可维护性]
       - 建议：具体改进建议
       - 示例：改进后的代码（如有）
    
    ### 建议优化（建议改进）
    1. 问题描述
       - 位置：代码行号
       - 建议：具体改进建议
    
    ### 优点（保持）
    1. 优点描述
    
    ### 总体评分
    - 规范性：X/10
    - 性能：X/10
    - 安全性：X/10
    - 可维护性：X/10""",
    
    "variables": ["language", "code", "review_dimensions"],
    "category": "code"
}

# 定义开发助手Skill
DEVELOPMENT_ASSISTANT_SKILL = {
    "name": "development_assistant",
    "description": "开发助手技能，帮助生成代码和设计方案",
    "system_prompt": """你是一位资深的软件架构师和开发专家，专门帮助用户开发医疗信息系统。
    
    你具备以下能力：
    1. 精通Spring Boot、MyBatis Plus等技术栈
    2. 熟悉医院业务流程和医疗规范
    3. 能够设计符合DDD架构的系统
    4. 熟悉数据库设计和优化
    5. 代码符合阿里巴巴Java开发规范
    
    生成代码时请遵循以下原则：
    - 代码结构清晰，易于理解
    - 添加必要的注释
    - 处理异常情况
    - 考虑性能和安全性""",
    
    "user_prompt_template": """请根据以下需求生成代码：
    
    需求描述：{requirement}
    
    上下文信息：
    {context}
    
    要求：
    1. 使用Spring Boot框架
    2. 包含完整的Entity、Service、Controller、Mapper层
    3. 添加必要的注释
    4. 处理异常情况
    
    输出格式：
    ```java
    // 完整代码
    ```""",
    
    "variables": ["requirement", "context"],
    "category": "development"
}
```

#### 步骤2：通过API添加Skill

```python
import requests

# API端点
API_BASE = "http://localhost:8000/api/v1"

def add_skill(skill_definition: dict, api_key: str):
    """添加Skill"""
    url = f"{API_BASE}/prompts/templates"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    response = requests.post(url, json=skill_definition, headers=headers)
    
    if response.status_code == 200:
        print(f"Skill添加成功: {skill_definition['name']}")
        return response.json()
    else:
        print(f"添加失败: {response.text}")
        return None

# 添加代码审查Skill
add_skill(CODE_REVIEW_SKILL, "your_api_key")

# 添加开发助手Skill
add_skill(DEVELOPMENT_ASSISTANT_SKILL, "your_api_key")
```

#### 步骤3：使用Skill

```python
def use_skill(skill_name: str, variables: dict, api_key: str):
    """使用Skill"""
    # 1. 格式化Prompt
    format_url = f"{API_BASE}/prompts/format"
    
    format_response = requests.post(
        format_url,
        json={
            "template_name": skill_name,
            "variables": variables
        },
        headers={"Authorization": f"Bearer {api_key}"}
    )
    
    if format_response.status_code != 200:
        print(f"格式化失败: {format_response.text}")
        return None
    
    prompt_data = format_response.json()
    
    # 2. 调用大模型
    chat_url = f"{API_BASE}/llm/chat"
    
    chat_response = requests.post(
        chat_url,
        json={
            "messages": [
                {"role": "system", "content": prompt_data["system"]},
                {"role": "user", "content": prompt_data["user"]}
            ],
            "model": "glm-4-flash",
            "temperature": 0.7
        },
        headers={"Authorization": f"Bearer {api_key}"}
    )
    
    if chat_response.status_code == 200:
        return chat_response.json()["content"]
    else:
        print(f"调用失败: {chat_response.text}")
        return None

# 使用代码审查Skill
result = use_skill(
    "code_review",
    {
        "language": "Java",
        "code": "public class User { private String name; public void setName(String name) { this.name = name; } }",
        "review_dimensions": "代码规范性、性能优化、安全性"
    },
    "your_api_key"
)

print(result)
```

## 三、RAG（检索增强生成）技术

### 3.1 RAG概念

RAG（Retrieval-Augmented Generation，检索增强生成）是一种结合信息检索和生成式AI的技术。

**工作原理：**
1. 将文档切分为小块并转换为向量
2. 存储到向量数据库中
3. 用户查询时，检索相关文档块
4. 将检索结果作为上下文输入大模型
5. 大模型基于上下文生成回答

**RAG的优势：**
- 减少幻觉（Hallucination）
- 基于事实回答
- 可追溯答案来源
- 支持知识更新

### 3.2 RAG参数配置

#### 核心参数说明

| 参数 | 说明 | 推荐范围 | 影响 |
|------|------|----------|------|
| chunk_size | 文档分块大小 | 256-1024 | 过大会丢失细节，过小会增加检索数量 |
| chunk_overlap | 分块重叠大小 | 50-200 | 保证上下文连贯性 |
| top_k | 检索结果数量 | 3-10 | 影响回答的全面性和速度 |
| similarity_threshold | 相似度阈值 | 0.6-0.8 | 过滤低质量结果 |
| embedding_model | 嵌入模型 | zhipuai-embedding | 影响检索精度 |

#### 配置文件示例

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # RAG参数配置
    default_chunk_size: int = 512          # 默认分块大小
    default_chunk_overlap: int = 50        # 默认重叠大小
    default_top_k: int = 5                 # 默认检索数量
    default_similarity_threshold: float = 0.7  # 默认相似度阈值
    
    # 向量数据库配置
    chroma_persist_dir: str = "./chroma_db"
    
    # 嵌入模型配置
    embedding_model: str = "zhipuai-embedding"
    
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
```

### 3.3 文档分块规则

#### 3.3.1 分块核心原则

**1. 完整性原则**
- 保持语义单元完整：不要在句子中间截断
- 保持段落结构：优先按段落边界分块
- 保持章节结构：使用标题作为分块边界

**2. 适当性原则**
- 块大小适中：太大影响检索精度，太小丢失上下文
- 重叠度合理：保证关键信息不被遗漏
- 长度均匀：避免过长或过短的极端情况

**3. 适配性原则**
- 根据文档类型选择策略
- 根据应用场景调整参数
- 根据模型限制优化分块

#### 3.3.2 分块策略选择指南

| 文档类型 | 推荐策略 | chunk_size | chunk_overlap | 适用场景 |
|---------|---------|-----------|---------------|---------|
| 技术文档 | 语义级分块 | 512-768 | 50-100 | 需要保持逻辑连贯性 |
| 代码文件 | 句子级分块 | 256-512 | 20-50 | 代码片段检索 |
| 新闻文章 | 段落级分块 | 384-512 | 30-80 | 事实性问答 |
| 规章制度 | 自定义分块 | 768-1024 | 100-200 | 完整条款保留 |
| 论文报告 | 章节级分块 | 1024-1536 | 150-300 | 长文本理解 |

#### 3.3.3 分块参数配置规范

**chunk_size（分块大小）选择规则**

```
通用规则：
- 短文本问答：256-384字符（约50-80个中文词）
- 中等文档检索：384-512字符（约80-100个中文词）
- 长文本理解：512-768字符（约100-150个中文词）
- 完整章节保留：768-1536字符（约150-300个中文词）
```

**chunk_overlap（重叠大小）配置规则**

```
重叠比例规则：
- 固定比例法：chunk_size × 10%-20%
  例：chunk_size=512，则chunk_overlap=50-100

语义连贯性规则：
- 句子级：重叠1-2个完整句子
- 段落级：重叠10%-15%
- 章节级：重叠15%-25%

避免遗漏规则：
- 关键实体前后必须重叠
- 重要结论前后必须重叠
- 逻辑连接词所在位置必须重叠
```

**特殊情况处理**

```python
# 1. 处理特殊符号和格式
SPECIAL_SEPARATORS = {
    "markdown": ["\n## ", "\n### ", "\n#### "],  # Markdown标题
    "code": ["\ndef ", "\nclass ", "\n    def "],  # 代码函数边界
    "legal": ["第.*条", ".*款"],  # 法律条款
    "contract": ["条款", "附件"]  # 合同条款
}

# 2. 最小/最大长度限制
MIN_CHUNK_LENGTH = 50    # 最小字符数，避免无意义片段
MAX_CHUNK_LENGTH = 2048  # 最大字符数，避免超出模型限制

# 3. 语义边界检测
def is_semantic_boundary(text, position):
    """检测是否为语义边界"""
    prev_char = text[position-1] if position > 0 else ""
    curr_char = text[position] if position < len(text) else ""
    
    # 句号、问号、感叹号后
    if prev_char in ["。", "？", "！"]:
        return True
    
    # 段落换行后
    if prev_char == "\n" and curr_char == "\n":
        return True
    
    return False
```

#### 3.3.4 分块质量评估

**评估指标**

```python
def evaluate_chunk_quality(chunks):
    """评估分块质量"""
    metrics = {
        # 1. 长度分布
        "avg_length": sum(len(c) for c in chunks) / len(chunks),
        "length_std": statistics.stdev(len(c) for c in chunks),
        
        # 2. 完整性指标
        "sentence_completeness": count_complete_sentences(chunks) / len(chunks),
        "boundary_alignment": check_boundary_alignment(chunks),
        
        # 3. 语义连贯性
        "coherence_score": measure_semantic_coherence(chunks),
        
        # 4. 检索效果
        "retrieval_precision": measure_retrieval_precision(chunks),
        "answer_quality": measure_answer_quality(chunks)
    }
    return metrics
```

**质量标准**

```
优秀分块：
- 长度标准差 < 30%平均长度
- 句子完整性 > 95%
- 边界对齐率 > 90%
- 语义连贯性 > 0.85

合格分块：
- 长度标准差 < 50%平均长度
- 句子完整性 > 85%
- 边界对齐率 > 75%
- 语义连贯性 > 0.7

需要优化：
- 存在极端长度块（<50或>2000字符）
- 句子完整性 < 80%
- 频繁在句子中间截断
- 语义连贯性 < 0.6
```

#### 3.3.5 常见问题与解决方案

**问题1：分块在句子中间截断**
```
原因：仅按字符数分块，未检测句子边界
解决：使用SentenceSplitter或在自定义逻辑中检测句子边界
```

**问题2：关键词被分割到两个块**
```
原因：重叠度不足或未在关键词边界分块
解决：增加chunk_overlap，或添加关键词检测逻辑
```

**问题3：块长度差异过大**
```
原因：固定分块大小，未考虑实际内容密度
解决：使用自适应分块，根据段落/章节动态调整
```

**问题4：上下文丢失**
```
原因：chunk_size过小或chunk_overlap过小
解决：适当增加chunk_size，保证overlap>10%
```

**问题5：检索结果不相关**
```
原因：分块粒度与查询不匹配
解决：根据查询类型调整分块策略（短查询用小块，长查询用大块）
```

### 3.4 文档分块策略

#### 句子级分块

```python
from llama_index.core.node_parser import SentenceSplitter

# 创建分块器
splitter = SentenceSplitter(
    chunk_size=512,        # 每块最大字符数
    chunk_overlap=50,      # 块之间重叠字符数
    paragraph_separator="\n\n",  # 段落分隔符
)

# 对文档进行分块
from llama_index.core import Document

documents = [
    Document(text="这是一段很长的文档内容...")
]

nodes = splitter.get_nodes_from_documents(documents)

print(f"分块数量: {len(nodes)}")
print(f"第一块内容: {nodes[0].text}")
```

#### 语义级分块

```python
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.zhipuai import ZhipuAIEmbedding

# 创建语义分块器
semantic_splitter = SemanticSplitterNodeParser(
    buffer_size=1,
    breakpoint_percentile_threshold=95,
    embed_model=ZhipuAIEmbedding(api_key="your_api_key", model="embedding-2")
)

# 对文档进行语义分块
nodes = semantic_splitter.get_nodes_from_documents(documents)

print(f"语义分块数量: {len(nodes)}")
```

#### 自定义分块

```python
from llama_index.core.node_parser import TextSplitter

class CustomSplitter(TextSplitter):
    """自定义分块器"""
    
    def split_text(self, text: str) -> List[str]:
        """自定义分块逻辑"""
        chunks = []
        
        # 按章节分块
        sections = text.split("## ")
        
        for section in sections:
            if not section.strip():
                continue
            
            # 如果章节太长，进一步分块
            if len(section) > 1000:
                sentences = section.split("。")
                current_chunk = ""
                
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) > 512:
                        chunks.append(current_chunk.strip())
                        current_chunk = ""
                    current_chunk += sentence + "。"
                
                if current_chunk:
                    chunks.append(current_chunk.strip())
            else:
                chunks.append(section.strip())
        
        return chunks

# 使用自定义分块器
custom_splitter = CustomSplitter(chunk_size=512, chunk_overlap=50)
nodes = custom_splitter.get_nodes_from_documents(documents)
```

### 3.4 知识库创建

#### 创建索引

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext
import chromadb

# 初始化ChromaDB客户端
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# 加载文档
documents = SimpleDirectoryReader("./docs").load_data()

# 创建分块器
from llama_index.core.node_parser import SentenceSplitter
splitter = SentenceSplitter(
    chunk_size=512,
    chunk_overlap=50
)

# 分块
nodes = splitter.get_nodes_from_documents(documents)

# 创建向量存储
collection = chroma_client.get_or_create_collection("my_knowledge_base")
vector_store = ChromaVectorStore(chroma_collection=collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# 创建索引
index = VectorStoreIndex(
    nodes=nodes,
    storage_context=storage_context,
    embed_model=ZhipuAIEmbedding(api_key="your_api_key", model="embedding-2")
)

print(f"索引创建成功，文档数: {len(documents)}, 节点数: {len(nodes)}")
```

#### 查询知识库

```python
def query_knowledge_base(index, query: str, top_k: int = 5):
    """查询知识库"""
    # 创建查询引擎
    query_engine = index.as_query_engine(
        similarity_top_k=top_k,
        similarity_cutoff=0.7  # 相似度阈值
    )
    
    # 执行查询
    response = query_engine.query(query)
    
    # 提取结果
    result = {
        "answer": str(response),
        "sources": [],
        "similarity_scores": []
    }
    
    for node in response.source_nodes:
        # 提取来源文件
        file_name = node.metadata.get("file_name", "unknown")
        result["sources"].append(file_name)
        
        # 提取相似度分数
        if hasattr(node, "score") and node.score is not None:
            result["similarity_scores"].append(float(node.score))
    
    return result

# 查询示例
result = query_knowledge_base(index, "什么是HIS系统？")
print(f"回答: {result['answer']}")
print(f"来源: {result['sources']}")
print(f"相似度: {result['similarity_scores']}")
```

### 3.5 RAG参数调优

#### chunk_size调优

```python
def test_chunk_sizes(documents, chunk_sizes: List[int]):
    """测试不同分块大小的效果"""
    results = {}
    
    for chunk_size in chunk_sizes:
        # 创建分块器
        splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=50
        )
        
        # 分块
        nodes = splitter.get_nodes_from_documents(documents)
        
        # 创建索引
        index = VectorStoreIndex(nodes=nodes)
        
        # 测试查询
        query_engine = index.as_query_engine(
            similarity_top_k=5,
            similarity_cutoff=0.7
        )
        
        test_queries = [
            "什么是HIS系统？",
            "门诊挂号流程是怎样的？"
        ]
        
        scores = []
        for query in test_queries:
            response = query_engine.query(query)
            if response.source_nodes:
                avg_score = sum(node.score for node in response.source_nodes) / len(response.source_nodes)
                scores.append(avg_score)
        
        results[chunk_size] = {
            "chunk_count": len(nodes),
            "avg_similarity": sum(scores) / len(scores) if scores else 0
        }
    
    return results

# 测试
chunk_sizes = [256, 512, 768, 1024]
results = test_chunk_sizes(documents, chunk_sizes)

for size, metrics in results.items():
    print(f"chunk_size={size}: 节点数={metrics['chunk_count']}, 平均相似度={metrics['avg_similarity']:.3f}")
```

#### top_k调优

```python
def test_top_k(index, query: str, top_k_values: List[int]):
    """测试不同top_k值的效果"""
    results = {}
    
    for top_k in top_k_values:
        query_engine = index.as_query_engine(
            similarity_top_k=top_k,
            similarity_cutoff=0.7
        )
        
        response = query_engine.query(query)
        
        results[top_k] = {
            "retrieved_count": len(response.source_nodes),
            "answer_length": len(str(response)),
            "answer": str(response)
        }
    
    return results

# 测试
top_k_values = [1, 3, 5, 7, 10]
results = test_top_k(index, "什么是HIS系统？", top_k_values)

for k, metrics in results.items():
    print(f"top_k={k}: 检索数={metrics['retrieved_count']}, 回答长度={metrics['answer_length']}")
```

### 3.6 高级RAG技术

#### 重排序（Re-ranking）

```python
from llama_index.core.postprocessor import SentenceTransformerRerank

# 创建重排序器
rerank = SentenceTransformerRerank(
    top_n=3,  # 保留前3个结果
    model="BAAI/bge-reranker-base"
)

# 创建查询引擎，添加重排序
query_engine = index.as_query_engine(
    similarity_top_k=10,  # 初步检索10个结果
    node_postprocessors=[rerank]  # 重排序到3个
)

response = query_engine.query("什么是HIS系统？")
print(f"重排序后的回答: {response}")
```

#### 混合检索

```python
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.query_engine import RetrieverQueryEngine

# 创建向量检索器
vector_retriever = index.as_retriever(similarity_top_k=5)

# 创建关键词检索器
keyword_retriever = index.as_retriever(
    mode="default",
    similarity_top_k=5
)

# 创建混合检索器
fusion_retriever = QueryFusionRetriever(
    retrievers=[vector_retriever, keyword_retriever],
    similarity_top_k=5
)

# 创建查询引擎
query_engine = RetrieverQueryEngine.from_args(fusion_retriever)

response = query_engine.query("什么是HIS系统？")
print(f"混合检索结果: {response}")
```

#### 多路召回

```python
def multi_retrieval_query(index, query: str):
    """多路召回策略"""
    # 路径1：高相似度
    engine1 = index.as_query_engine(
        similarity_top_k=3,
        similarity_cutoff=0.8
    )
    
    # 路径2：中等相似度，更多结果
    engine2 = index.as_query_engine(
        similarity_top_k=10,
        similarity_cutoff=0.6
    )
    
    # 路径3：关键词匹配
    engine3 = index.as_query_engine(
        mode="default",
        similarity_top_k=5
    )
    
    # 执行查询
    result1 = engine1.query(query)
    result2 = engine2.query(query)
    result3 = engine3.query(query)
    
    # 合并结果
    combined_sources = set()
    for response in [result1, result2, result3]:
        for node in response.source_nodes:
            combined_sources.add(node.metadata.get("file_name", "unknown"))
    
    return {
        "answer": str(result1),
        "all_sources": list(combined_sources)
    }

# 使用
result = multi_retrieval_query(index, "什么是HIS系统？")
print(f"回答: {result['answer']}")
print(f"所有来源: {result['all_sources']}")
```

## 四、Skill与RAG结合

### 4.1 带知识库的Skill

```python
class RAGSkill:
    """带RAG的Skill"""
    
    def __init__(self, name: str, kb_index: VectorStoreIndex, api_key: str):
        self.name = name
        self.kb_index = kb_index
        self.client = ZhipuAI(api_key=api_key)
    
    def execute(self, query: str, top_k: int = 5) -> str:
        """执行Skill"""
        # 1. 从知识库检索
        query_engine = self.kb_index.as_query_engine(
            similarity_top_k=top_k,
            similarity_cutoff=0.7
        )
        
        retrieval_result = query_engine.query(query)
        
        # 2. 提取上下文
        context = "\n\n".join([
            node.node.text for node in retrieval_result.source_nodes
        ])
        
        # 3. 构建Prompt
        prompt = f"""
        基于以下知识回答问题：
        
        知识库内容：
        {context}
        
        问题：
        {query}
        
        要求：
        1. 只使用知识库中的信息回答
        2. 如果知识库中没有相关信息，请说明
        3. 引用具体的来源文件
        """
        
        # 4. 调用大模型
        response = self.client.chat.completions.create(
            model="glm-4-flash",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content

# 使用
his_kb_skill = RAGSkill("his_qa", index, "your_api_key")
answer = his_kb_skill.execute("门诊挂号需要哪些信息？")
print(answer)
```

### 4.2 HIS系统问答Skill

```python
# 创建HIS问答Skill
HIS_QA_SKILL = {
    "name": "his_qa",
    "description": "HIS系统知识问答",
    "system_prompt": """你是一位HIS系统专家，能够基于知识库回答用户问题。
    
    回答原则：
    1. 只使用提供的知识库内容
    2. 回答准确、简洁
    3. 引用来源文件
    4. 如果知识库中没有相关信息，明确说明""",
    
    "user_prompt_template": """基于以下知识回答问题：
    
    知识库内容：
    {context}
    
    问题：
    {query}
    
    回答格式：
    ## 回答
    [你的回答]
    
    ## 来源
    - [文件名1]
    - [文件名2]""",
    
    "variables": ["context", "query"],
    "category": "qa",
    "use_rag": True  # 标记需要使用RAG
}

# 执行函数
def execute_rag_skill(
    skill_name: str,
    query: str,
    kb_index: VectorStoreIndex,
    api_key: str
) -> str:
    """执行RAG Skill"""
    # 1. 检索知识库
    query_engine = kb_index.as_query_engine(
        similarity_top_k=5,
        similarity_cutoff=0.7
    )
    
    retrieval_result = query_engine.query(query)
    
    # 2. 提取上下文
    context_parts = []
    sources = []
    
    for node in retrieval_result.source_nodes:
        context_parts.append(f"来源：{node.metadata.get('file_name', 'unknown')}\n内容：{node.node.text}")
        sources.append(node.metadata.get('file_name', 'unknown'))
    
    context = "\n\n".join(context_parts)
    
    # 3. 格式化Prompt
    manager = PromptManager()
    formatted = manager.format_prompt(
        db,  # 数据库会话
        skill_name,
        {
            "context": context,
            "query": query
        }
    )
    
    # 4. 调用大模型
    client = ZhipuAI(api_key=api_key)
    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=[
            {"role": "system", "content": formatted["system"]},
            {"role": "user", "content": formatted["user"]}
        ]
    )
    
    return response.choices[0].message.content

# 使用
answer = execute_rag_skill("his_qa", "门诊挂号流程是什么？", index, "your_api_key")
print(answer)
```

## 五、最佳实践

### 5.1 Skill设计原则

1. **单一职责**：每个Skill只负责一个任务
2. **清晰描述**：System Prompt要明确Skill的职责和边界
3. **变量设计**：变量名要语义化，数量不宜过多
4. **输出格式**：明确指定输出格式，便于解析

### 5.2 RAG参数调优建议

| 场景 | chunk_size | top_k | similarity_threshold |
|------|------------|-------|---------------------|
| 精确问答 | 256-512 | 3-5 | 0.75-0.85 |
| 概念解释 | 512-768 | 5-8 | 0.65-0.75 |
| 综合分析 | 768-1024 | 8-10 | 0.60-0.70 |

### 5.3 性能优化

```python
# 1. 使用缓存
from functools import lru_cache

@lru_cache(maxsize=100)
def get_template(name: str) -> PromptTemplate:
    """缓存的模板获取"""
    return prompt_manager.get_template(db, name)

# 2. 批量查询
def batch_query(index, queries: List[str]) -> List[str]:
    """批量查询"""
    results = []
    for query in queries:
        result = query_knowledge_base(index, query)
        results.append(result)
    return results

# 3. 异步处理
import asyncio
from zhipuai import AsyncZhipuAI

async def async_query(client, query: str) -> str:
    """异步查询"""
    response = await client.chat.completions.acreate(
        model="glm-4-flash",
        messages=[{"role": "user", "content": query}]
    )
    return response.choices[0].message.content

async def batch_async_query(queries: List[str]) -> List[str]:
    """批量异步查询"""
    client = AsyncZhipuAI(api_key="your_api_key")
    tasks = [async_query(client, query) for query in queries]
    return await asyncio.gather(*tasks)
```

## 六、总结

### 关键要点

1. **Skill机制**
   - 通过Prompt模板实现能力模块化
   - 支持动态添加和配置
   - 便于复用和管理

2. **RAG技术**
   - 结合检索和生成
   - 减少幻觉，提高准确性
   - 关键参数需要根据场景调优

3. **最佳实践**
   - Skill设计遵循单一职责原则
   - RAG参数根据应用场景选择
   - 注意性能优化和成本控制

### 下一步学习

- 深入学习Prompt工程
- 探索多Agent协作
- 学习评估指标和测试方法
- 研究更高级的RAG技术

### 参考资源

- LlamaIndex文档：https://docs.llamaindex.ai/
- ChromaDB文档：https://docs.trychroma.com/
- RAG最佳实践：https://www.anthropic.com/index/retrieval-augmented-generation
