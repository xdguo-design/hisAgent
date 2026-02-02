import requests
import json

url = "http://localhost:8000/api/v1/knowledge/test_kb/agentic-query"
headers = {"Content-Type": "application/json"}
data = {
    "query": "如何使用Python进行文件操作？请给出具体示例。",
    "knowledge_base_name": "test_kb",
    "config": {
        "max_retrieval_rounds": 3,
        "quality_threshold": 0.6,
        "enable_task_decomposition": True,
        "enable_self_reflection": True
    }
}

try:
    response = requests.post(url, headers=headers, json=data, timeout=180)
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"Agentic RAG 查询结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
except Exception as e:
    print(f"请求失败: {str(e)}")
