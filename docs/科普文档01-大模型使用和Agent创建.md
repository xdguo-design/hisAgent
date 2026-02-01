# 大模型使用和Agent创建科普文档

## 一、大模型基础概念

### 1.1 什么是大语言模型

大语言模型（Large Language Model，简称LLM）是基于深度学习的自然语言处理模型，通过海量文本数据训练而成。它能够理解和生成人类语言，完成文本生成、问答、翻译、代码编写等多种任务。

**核心特点：**
- 海量参数：通常有数十亿到万亿个参数
- 上下文理解：能够理解长文本的上下文关系
- 泛化能力：无需额外训练即可处理多种任务
- 涌现能力：随着模型规模增大，会出现意想不到的新能力

### 1.2 主流大模型介绍

#### 智谱AI（GLM系列）
- **模型系列**：GLM-4、GLM-4-Flash、GLM-3-Turbo等
- **优势**：中文理解能力强，性价比高
- **适用场景**：中文问答、代码生成、文档写作
- **API调用**：简单易用，支持流式输出

#### 其他主流模型
- **OpenAI GPT-4**：通用能力强，但成本较高
- **Claude**：长文本处理能力强
- **文心一言**：百度出品，中文优化好
- **通义千问**：阿里出品，多场景适用

## 二、大模型API使用

### 2.1 API密钥获取

1. 访问智谱AI开放平台：https://open.bigmodel.cn
2. 注册账号并完成实名认证
3. 进入API管理页面，创建API密钥
4. 保存密钥，后续用于代码调用

### 2.2 基础API调用

#### Python SDK调用示例

```python
from zhipuai import ZhipuAI

# 初始化客户端
client = ZhipuAI(api_key="your_api_key")

# 发起对话请求
response = client.chat.completions.create(
    model="glm-4-flash",  # 模型名称
    messages=[
        {"role": "system", "content": "你是一个专业的医疗系统开发专家"},
        {"role": "user", "content": "什么是HIS系统？"}
    ],
    temperature=0.7,      # 温度参数（0-1）
    max_tokens=2000      # 最大输出token数
)

# 获取响应内容
answer = response.choices[0].message.content
print(answer)
```

#### 关键参数说明

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| model | 模型名称 | glm-4-flash（性价比） |
| temperature | 温度参数，控制随机性 | 0.5-0.7（平衡） |
| max_tokens | 最大输出token数 | 2000-4000 |
| top_p | 核采样参数 | 0.9（常用） |
| stream | 是否流式输出 | true（长文本推荐） |

### 2.3 流式输出处理

```python
from zhipuai import ZhipuAI

client = ZhipuAI(api_key="your_api_key")

# 流式调用
response = client.chat.completions.create(
    model="glm-4-flash",
    messages=[{"role": "user", "content": "详细介绍HIS系统的架构"}],
    stream=True  # 启用流式输出
)

# 逐块处理响应
for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

### 2.4 错误处理

```python
from zhipuai import ZhipuAI
from zhipuai.core._errors import APIRequestError

client = ZhipuAI(api_key="your_api_key")

try:
    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "user", "content": "测试消息"}]
    )
except APIRequestError as e:
    if e.status_code == 401:
        print("API密钥无效，请检查")
    elif e.status_code == 429:
        print("请求频率超限，请稍后重试")
    else:
        print(f"API调用失败: {e}")
except Exception as e:
    print(f"未知错误: {e}")
```

## 三、Agent概念与创建

### 3.1 什么是Agent

Agent（智能体）是一个能够感知环境、进行决策并执行动作的自主系统。在AI领域，Agent通常指能够使用大模型完成复杂任务的系统。

**Agent的核心能力：**
- **感知**：理解用户意图和上下文
- **推理**：分析问题并制定解决方案
- **记忆**：存储和检索历史信息
- **工具调用**：使用外部工具完成任务
- **规划**：将复杂任务分解为子任务

### 3.2 Agent vs 传统大模型调用

| 特性 | 传统大模型调用 | Agent |
|------|----------------|-------|
| 记忆能力 | 无状态，每次调用独立 | 有记忆，能记住上下文 |
| 工具使用 | 仅依赖模型自身知识 | 可调用外部工具/API |
| 任务规划 | 单轮对话 | 多步规划与执行 |
| 自主性 | 被动响应 | 主动决策 |
| 适用场景 | 简单问答、文本生成 | 复杂任务、工作流 |

### 3.3 Agent架构设计

#### 基础架构

```
┌─────────────────────────────────────────────────┐
│                   用户请求                       │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│              Agent 核心层                        │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │ 意图识别 │→ │ 任务规划 │→ │ 工具调度 │        │
│  └─────────┘  └─────────┘  └─────────┘        │
└──────────────────┬──────────────────────────────┘
                   │
       ┌───────────┼───────────┐
       ▼           ▼           ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ 大模型   │ │ 知识库   │ │ 工具集   │
└──────────┘ └──────────┘ └──────────┘
```

#### HIS Agent实现架构

```python
class HISExpert:
    """
    HIS领域专家Agent
    
    核心能力：
    1. 代码审查
    2. 开发助手
    3. 知识问答
    4. 工作流设计
    """
    
    def __init__(self):
        self.llm_service = LLMService()  # 大模型服务
        self.kb_service = KnowledgeBaseService()  # 知识库
        self.prompt_manager = PromptManager()  # 提示词管理
    
    def code_review(self, code: str) -> str:
        """代码审查能力"""
        # 使用专门的提示词模板
        prompt = self.prompt_manager.format_prompt(
            "code_review",
            {"code": code}
        )
        return self.llm_service.chat(prompt)
    
    def development_assistant(self, requirement: str) -> str:
        """开发助手能力"""
        prompt = self.prompt_manager.format_prompt(
            "development_assistant",
            {"requirement": requirement}
        )
        return self.llm_service.chat(prompt)
```

### 3.4 创建一个简单Agent

#### 步骤1：定义Agent核心类

```python
from typing import Dict, List, Optional
from zhipuai import ZhipuAI

class SimpleAgent:
    """简单Agent实现"""
    
    def __init__(self, api_key: str):
        self.client = ZhipuAI(api_key=api_key)
        self.memory: List[Dict] = []  # 对话记忆
        self.system_prompt = "你是一个有帮助的助手"
    
    def set_system_prompt(self, prompt: str):
        """设置系统提示词"""
        self.system_prompt = prompt
    
    def chat(self, user_message: str) -> str:
        """处理用户消息"""
        # 添加用户消息到记忆
        self.memory.append({
            "role": "user",
            "content": user_message
        })
        
        # 构建消息列表
        messages = [
            {"role": "system", "content": self.system_prompt}
        ] + self.memory
        
        # 调用大模型
        response = self.client.chat.completions.create(
            model="glm-4-flash",
            messages=messages
        )
        
        # 获取回复
        assistant_message = response.choices[0].message.content
        
        # 添加到记忆
        self.memory.append({
            "role": "assistant",
            "content": assistant_message
        })
        
        return assistant_message
    
    def clear_memory(self):
        """清空记忆"""
        self.memory = []
```

#### 步骤2：使用Agent

```python
# 创建Agent实例
agent = SimpleAgent(api_key="your_api_key")

# 设置系统提示词
agent.set_system_prompt(
    "你是一个专业的医疗系统开发专家，"
    "专门帮助用户开发和维护HIS系统"
)

# 对话示例
response1 = agent.chat("什么是HIS系统？")
print(f"AI: {response1}")

response2 = agent.chat("如何设计患者信息表？")
print(f"AI: {response2}")

# 清空记忆
agent.clear_memory()
```

### 3.5 带记忆的Agent

#### 短期记忆（对话历史）

```python
class AgentWithMemory:
    """带记忆的Agent"""
    
    def __init__(self, api_key: str, max_history: int = 10):
        self.client = ZhipuAI(api_key=api_key)
        self.max_history = max_history
        self.conversation_history: List[Dict] = []
    
    def add_to_history(self, role: str, content: str):
        """添加到对话历史"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        # 限制历史长度
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history * 2:]
    
    def get_context(self) -> List[Dict]:
        """获取上下文"""
        return [{"role": "system", "content": "你是一个有帮助的助手"}] + self.conversation_history
    
    def chat(self, user_message: str) -> str:
        """处理对话"""
        self.add_to_history("user", user_message)
        
        response = self.client.chat.completions.create(
            model="glm-4-flash",
            messages=self.get_context()
        )
        
        assistant_message = response.choices[0].message.content
        self.add_to_history("assistant", assistant_message)
        
        return assistant_message
```

#### 长期记忆（向量数据库）

```python
from llama_index.core import VectorStoreIndex, Document

class AgentWithLongTermMemory:
    """带长期记忆的Agent"""
    
    def __init__(self, api_key: str):
        self.client = ZhipuAI(api_key=api_key)
        self.vector_index: Optional[VectorStoreIndex] = None
    
    def store_memory(self, content: str, metadata: Dict = None):
        """存储记忆"""
        doc = Document(text=content, metadata=metadata or {})
        
        if self.vector_index is None:
            self.vector_index = VectorStoreIndex.from_documents([doc])
        else:
            self.vector_index.insert(doc)
    
    def retrieve_memory(self, query: str, top_k: int = 3) -> List[str]:
        """检索相关记忆"""
        if self.vector_index is None:
            return []
        
        query_engine = self.vector_index.as_query_engine(
            similarity_top_k=top_k
        )
        response = query_engine.query(query)
        
        return [node.node.text for node in response.source_nodes]
    
    def chat_with_memory(self, user_message: str) -> str:
        """结合记忆的对话"""
        # 检索相关记忆
        relevant_memories = self.retrieve_memory(user_message)
        
        # 构建提示词
        context = "\n".join(relevant_memories)
        prompt = f"""
        相关记忆：
        {context}
        
        用户问题：
        {user_message}
        """
        
        # 调用大模型
        response = self.client.chat.completions.create(
            model="glm-4-flash",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # 存储这次对话
        self.store_memory(
            f"用户问：{user_message}\n回答：{response.choices[0].message.content}"
        )
        
        return response.choices[0].message.content
```

## 四、HIS Agent实战

### 4.1 HIS系统需求

HIS（Hospital Information System，医院信息系统）是一个复杂的医疗信息化系统，包含多个子系统：

- 门诊挂号系统
- 住院管理系统
- 电子病历系统
- 药房管理系统
- 检验检查系统
- 财务结算系统

### 4.2 创建HIS Agent

```python
class HISAgent:
    """HIS领域专家Agent"""
    
    def __init__(self, api_key: str):
        self.client = ZhipuAI(api_key=api_key)
        self.system_prompt = """
        你是一位资深的HIS系统架构师和开发专家，具有以下能力：
        1. 熟悉医院业务流程和医疗规范
        2. 精通Spring Boot、MyBatis Plus等技术栈
        3. 能够设计符合DDD架构的系统
        4. 熟悉数据库设计和优化
        """
    
    def design_architecture(self, requirement: str) -> str:
        """设计系统架构"""
        prompt = f"""
        请根据以下需求设计HIS系统架构：
        {requirement}
        
        要求：
        1. 使用DDD分层架构
        2. 定义核心领域模型
        3. 设计API接口
        4. 说明技术选型
        """
        
        response = self.client.chat.completions.create(
            model="glm-4-flash",
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content
    
    def generate_code(self, module: str, description: str) -> str:
        """生成代码"""
        prompt = f"""
        请生成以下HIS模块的代码：
        模块：{module}
        功能描述：{description}
        
        要求：
        1. 使用Spring Boot框架
        2. 符合阿里巴巴Java开发规范
        3. 包含完整的Service、Controller、Mapper层
        4. 添加必要的注释
        """
        
        response = self.client.chat.completions.create(
            model="glm-4-flash",
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # 降低温度以获得更确定的代码
            max_tokens=4000
        )
        
        return response.choices[0].message.content
    
    def review_code(self, code: str) -> str:
        """代码审查"""
        prompt = f"""
        请审查以下代码，指出问题和改进建议：
        {code}
        
        审查维度：
        1. 代码规范性
        2. 性能优化
        3. 安全性
        4. 可维护性
        """
        
        response = self.client.chat.completions.create(
            model="glm-4-flash",
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content
```

### 4.3 使用HIS Agent

```python
# 创建HIS Agent
his_agent = HISAgent(api_key="your_api_key")

# 示例1：设计门诊挂号系统架构
architecture = his_agent.design_architecture("""
实现患者门诊挂号功能，包含：
1. 患者信息录入
2. 科室选择
3. 医生排班查询
4. 挂号费结算
""")
print(architecture)

# 示例2：生成患者信息管理代码
code = his_agent.generate_code(
    "患者信息管理",
    "实现患者信息的增删改查功能，包含姓名、身份证号、电话号码等字段"
)
print(code)

# 示例3：代码审查
review = his_agent.review_code(code)
print(review)
```

## 五、最佳实践

### 5.1 Prompt工程

#### 好的Prompt特征
- **明确目标**：清楚说明要完成什么任务
- **提供上下文**：给出必要的背景信息
- **指定格式**：说明期望的输出格式
- **约束条件**：明确限制和边界

#### Prompt模板化

```python
PROMPT_TEMPLATES = {
    "code_generation": """
    请生成{language}代码，完成以下功能：
    {description}
    
    要求：
    {requirements}
    
    输出格式：
    ```{language}
    // 代码
    ```
    """,
    
    "code_review": """
    请审查以下代码：
    ```{language}
    {code}
    ```
    
    审查维度：
    {review_dimensions}
    
    输出格式：
    ## 问题列表
    1. 问题描述
       - 位置：代码行号
       - 严重程度：高/中/低
       - 建议：改进建议
    """
}

def format_prompt(template_name: str, **kwargs) -> str:
    """格式化Prompt"""
    template = PROMPT_TEMPLATES[template_name]
    return template.format(**kwargs)
```

### 5.2 错误处理

```python
import time
from zhipuai.core._errors import APIRequestError

def call_with_retry(
    agent: SimpleAgent,
    message: str,
    max_retries: int = 3,
    retry_delay: float = 1.0
) -> Optional[str]:
    """带重试的调用"""
    for attempt in range(max_retries):
        try:
            return agent.chat(message)
        except APIRequestError as e:
            if e.status_code == 429:
                print(f"频率限制，等待{retry_delay}秒后重试...")
                time.sleep(retry_delay)
                retry_delay *= 2  # 指数退避
            else:
                print(f"API调用失败: {e}")
                return None
        except Exception as e:
            print(f"未知错误: {e}")
            return None
    
    print(f"达到最大重试次数{max_retries}")
    return None
```

### 5.3 成本控制

```python
class CostControlledAgent:
    """成本控制的Agent"""
    
    def __init__(self, api_key: str, daily_budget: float = 10.0):
        self.client = ZhipuAI(api_key=api_key)
        self.daily_budget = daily_budget
        self.daily_cost = 0.0
        self.token_prices = {
            "glm-4-flash": {"input": 0.0001, "output": 0.0002},  # 每1K token价格
            "glm-4": {"input": 0.001, "output": 0.002}
        }
    
    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """估算成本"""
        prices = self.token_prices.get(model, {})
        input_cost = input_tokens / 1000 * prices.get("input", 0)
        output_cost = output_tokens / 1000 * prices.get("output", 0)
        return input_cost + output_cost
    
    def chat(self, message: str, model: str = "glm-4-flash") -> str:
        """带成本控制的对话"""
        # 检查预算
        if self.daily_cost >= self.daily_budget:
            raise Exception("今日预算已用完")
        
        # 调用API
        response = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": message}]
        )
        
        # 计算成本
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cost = self.estimate_cost(model, input_tokens, output_tokens)
        
        self.daily_cost += cost
        print(f"本次调用成本: ¥{cost:.4f}, 今日累计: ¥{self.daily_cost:.4f}")
        
        return response.choices[0].message.content
```

## 六、总结

### 关键要点

1. **大模型选择**
   - 中文场景优先考虑智谱AI
   - 成本敏感选择Flash版本
   - 复杂任务选择完整版模型

2. **Agent设计原则**
   - 明确领域边界
   - 合理使用记忆机制
   - 模块化设计便于扩展

3. **工程实践**
   - 完善的错误处理
   - 成本控制机制
   - Prompt模板化

4. **HIS系统特点**
   - 业务复杂度高
   - 需要领域专业知识
   - 安全性和稳定性要求高

### 下一步学习

- 深入了解Prompt工程技巧
- 学习RAG（检索增强生成）技术
- 掌握Agent工具调用机制
- 探索多Agent协作模式

### 参考资源

- 智谱AI文档：https://open.bigmodel.cn/dev/api
- LlamaIndex文档：https://docs.llamaindex.ai/
- Agent开发最佳实践：https://lilianweng.github.io/posts/2023-06-23-agent/
