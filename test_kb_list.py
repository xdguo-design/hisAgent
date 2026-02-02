import requests
import json

url = "http://localhost:8000/api/v1/knowledge/list"
headers = {"Content-Type": "application/json"}

try:
    response = requests.get(url, headers=headers, timeout=30)
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"知识库列表: {json.dumps(result, ensure_ascii=False, indent=2)}")
except Exception as e:
    print(f"请求失败: {str(e)}")
