# Agentic RAG 测试文档

## 什么是 Agentic RAG？

Agentic RAG（Agentic Retrieval-Augmented Generation）是一种智能检索增强生成系统，它通过引入代理机制来改进传统的 RAG 系统。

## 核心特性

### 1. 查询路由（Query Routing）
系统会智能分析查询的类型和意图，然后选择最佳的检索策略。支持的查询类型包括：
- **事实性查询**（Factual）：具体事实、数据查询
- **概念性查询**（Conceptual）：定义、原理、理论查询
- **程序性查询**（Procedural）：步骤、流程、操作指南
- **比较性查询**（Comparative）：对比、差异分析
- **分析性查询**（Analytical）：深入分析、推理
- **多跳查询**（Multi-hop）：需要多次检索的复杂问题
- **模糊查询**（Ambiguous）：需要澄清的问题

### 2. 任务分解（Task Decomposition）
对于复杂查询，系统会自动将其分解为多个可管理的子任务：
- 每个子任务可以独立执行
- 识别任务之间的依赖关系
- 标记可以并行执行的任务

### 3. 动态检索（Dynamic Retrieval）
根据查询类型和上下文动态调整检索参数：
- 不同查询类型使用不同的 top_k 值
- 自适应调整相似度阈值
- 优化检索结果的召回率和准确率

### 4. 自反思（Self-Reflection）
评估检索质量，必要时重新检索：
- 评估答案的相关性、完整性、准确性、清晰性
- 如果质量低于阈值，自动进行重新检索
- 提供改进建议

### 5. 工具调用（Tool Use）
支持集成外部工具来扩展能力。

## 使用场景

1. **复杂问题回答**：需要多步骤推理的问题
2. **多文档分析**：跨多个文档的综合分析
3. **决策支持**：基于大量信息的决策辅助
4. **知识管理**：企业知识库的智能检索

## 与传统 RAG 的区别

| 特性 | 传统 RAG | Agentic RAG |
|------|----------|-------------|
| 查询分析 | 简单关键词匹配 | 智能查询路由 |
| 复杂查询 | 单次检索 | 任务分解 |
| 检索策略 | 固定参数 | 动态调整 |
| 质量控制 | 无 | 自反思机制 |
| 推理能力 | 有限 | 多步推理 |

## 技术实现

系统基于以下技术栈：
- **ZhipuAI GLM-4**：大语言模型
- **LlamaIndex**：检索增强框架
- **ChromaDB**：向量数据库
- **FastAPI**：API 服务框架

## API 端点

### 创建知识库
```bash
POST /api/knowledge
Content-Type: application/json

{
  "name": "test_kb",
  "path": "./test_kb",
  "chunk_size": 512,
  "chunk_overlap": 50,
  "description": "测试知识库"
}
```

### 传统 RAG 查询
```bash
POST /api/knowledge/{name}/query
Content-Type: application/json

{
  "query": "什么是 Agentic RAG？",
  "top_k": 5,
  "similarity_threshold": 0.7
}
```

### Agentic RAG 查询
```bash
POST /api/knowledge/{name}/agentic-query
Content-Type: application/json

{
  "knowledge_base_name": "test_kb",
  "query": "Agentic RAG 相比传统 RAG 有什么优势？",
  "config": {
    "max_retrieval_rounds": 3,
    "quality_threshold": 0.6,
    "enable_task_decomposition": true,
    "enable_self_reflection": true
  }
}
```

## 配置参数

### AgenticRAGConfig
- `max_retrieval_rounds`：最大检索轮数（默认：3）
- `quality_threshold`：质量评分阈值（默认：0.6）
- `enable_task_decomposition`：启用任务分解（默认：true）
- `enable_self_reflection`：启用自反思（默认：true）
- `enable_tool_use`：启用工具调用（默认：false）
- `default_temperature`：默认温度参数（默认：0.3）
- `reasoning_temperature`：推理温度参数（默认：0.7）

## 最佳实践

1. **选择合适的 chunk_size**：根据文档类型调整，技术文档建议 512-1024
2. **调整相似度阈值**：根据数据质量调整，一般 0.6-0.8
3. **启用自反思**：对准确性要求高的场景建议启用
4. **任务分解**：复杂问题查询建议启用

## 总结

Agentic RAG 通过引入代理机制，显著提升了检索增强生成的智能化水平，能够更好地处理复杂查询和提供高质量的答案。
