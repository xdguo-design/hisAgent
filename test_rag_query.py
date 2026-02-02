import requests
import json

url = "http://localhost:8000/api/v1/knowledge/test_kb/query"
headers = {"Content-Type": "application/json"}
data = {
    "query": "什么是Agentic RAG？",
    "top_k": 3
}

try:
    response = requests.post(url, headers=headers, json=data, timeout=120)
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"查询结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
except Exception as e:
    print(f"请求失败: {str(e)}")
