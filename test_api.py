import requests
import json

url = "http://localhost:8000/api/v1/knowledge/create"
headers = {"Content-Type": "application/json"}
data = {
    "name": "test_kb",
    "path": "d:\\workspace\\python\\hisAgent\\test_kb",
    "description": "测试知识库 - 使用BGE模型"
}

response = requests.post(url, headers=headers, json=data)
print(f"状态码: {response.status_code}")
print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
