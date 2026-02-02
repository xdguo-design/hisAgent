import requests
import json
import time

url = "http://localhost:8000/api/v1/knowledge/create"
headers = {"Content-Type": "application/json"}
data = {
    "name": "test_kb",
    "path": "d:\\workspace\\python\\hisAgent\\test_kb",
    "description": "测试知识库 - 使用BGE模型"
}

try:
    response = requests.post(url, headers=headers, json=data, timeout=30)
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
except Exception as e:
    print(f"请求失败: {str(e)}")
