import requests
import json

url = "http://localhost:8000/api/v1/knowledge/test_kb/delete"
headers = {"Content-Type": "application/json"}

try:
    response = requests.post(url, headers=headers, timeout=30)
    print(f"删除状态码: {response.status_code}")
    print(f"删除响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
except Exception as e:
    print(f"删除请求失败: {str(e)}")

url = "http://localhost:8000/api/v1/knowledge/create"
headers = {"Content-Type": "application/json"}
data = {
    "name": "test_kb",
    "path": "d:\\workspace\\python\\hisAgent\\test_kb",
    "description": "测试知识库 - 使用BGE模型",
    "embedding_model": "BAAI/bge-base-zh-v1.5"
}

try:
    response = requests.post(url, headers=headers, json=data, timeout=60)
    print(f"创建状态码: {response.status_code}")
    print(f"创建响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
except Exception as e:
    print(f"创建请求失败: {str(e)}")
