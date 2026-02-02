# Python 编程指南

## 基础语法

### 变量和数据类型

Python 支持多种数据类型：

```python
# 数字类型
age = 25
price = 19.99
is_active = True

# 字符串
name = "Python"
message = 'Hello, World!'

# 列表
numbers = [1, 2, 3, 4, 5]
fruits = ["apple", "banana", "orange"]

# 字典
person = {
    "name": "Alice",
    "age": 30,
    "city": "Beijing"
}

# 元组
coordinates = (10, 20)

# 集合
unique_numbers = {1, 2, 3, 3, 2, 1}  # 结果：{1, 2, 3}
```

### 控制流程

#### 条件语句

```python
if age >= 18:
    print("成年人")
elif age >= 13:
    print("青少年")
else:
    print("儿童")
```

#### 循环

```python
# for 循环
for i in range(5):
    print(i)

# 遍历列表
for fruit in fruits:
    print(fruit)

# while 循环
count = 0
while count < 5:
    print(count)
    count += 1
```

### 函数定义

```python
def greet(name, greeting="Hello"):
    """
    问候函数
    
    Args:
        name: 姓名
        greeting: 问候语（默认 "Hello"）
    
    Returns:
        问候消息
    """
    return f"{greeting}, {name}!"

# 调用函数
message = greet("Alice")
print(message)  # 输出：Hello, Alice!
```

## 面向对象编程

### 类和对象

```python
class Dog:
    species = "Canis familiaris"  # 类属性
    
    def __init__(self, name, age):
        """初始化方法"""
        self.name = name  # 实例属性
        self.age = age
    
    def bark(self):
        """实例方法"""
        return f"{self.name} says Woof!"
    
    @classmethod
    def from_string(cls, info_str):
        """类方法"""
        name, age = info_str.split(",")
        return cls(name, int(age))
    
    @staticmethod
    def is_dog(animal):
        """静态方法"""
        return animal.species == "Canis familiaris"

# 创建对象
dog1 = Dog("Buddy", 3)
print(dog1.bark())  # 输出：Buddy says Woof!
```

### 继承

```python
class GoldenRetriever(Dog):
    def __init__(self, name, age, color):
        super().__init__(name, age)
        self.color = color
    
    def fetch(self):
        return f"{self.name} fetches the ball!"

golden = GoldenRetriever("Max", 5, "golden")
print(golden.fetch())
```

## 文件操作

### 读写文件

```python
# 读取文件
with open("file.txt", "r", encoding="utf-8") as f:
    content = f.read()
    print(content)

# 写入文件
with open("output.txt", "w", encoding="utf-8") as f:
    f.write("Hello, World!")

# 追加写入
with open("log.txt", "a", encoding="utf-8") as f:
    f.write("New log entry\n")
```

### JSON 处理

```python
import json

# 读取 JSON
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 写入 JSON
with open("output.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

## 异常处理

```python
try:
    result = 10 / 0
except ZeroDivisionError as e:
    print(f"错误：{e}")
except Exception as e:
    print(f"未知错误：{e}")
else:
    print("没有异常")
finally:
    print("无论是否有异常都会执行")
```

## 常用模块

### datetime 模块

```python
from datetime import datetime, timedelta

now = datetime.now()
print(f"当前时间：{now}")

tomorrow = now + timedelta(days=1)
print(f"明天：{tomorrow}")
```

### os 模块

```python
import os

# 获取当前目录
current_dir = os.getcwd()

# 列出目录内容
files = os.listdir(".")

# 创建目录
os.makedirs("new_folder", exist_ok=True)

# 检查文件是否存在
if os.path.exists("file.txt"):
    print("文件存在")
```

### requests 模块

```python
import requests

# GET 请求
response = requests.get("https://api.example.com/data")
data = response.json()

# POST 请求
payload = {"key": "value"}
response = requests.post("https://api.example.com/submit", json=payload)
```

## 最佳实践

### 1. 使用虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 2. 遵循 PEP 8 代码规范

- 使用 4 个空格缩进
- 变量名使用小写字母和下划线
- 类名使用大驼峰命名法
- 每行代码不超过 79 个字符

### 3. 编写文档字符串

```python
def calculate_area(length, width):
    """
    计算矩形面积
    
    Args:
        length: 长度
        width: 宽度
    
    Returns:
        面积
    """
    return length * width
```

### 4. 使用列表推导式

```python
# 传统方式
squares = []
for i in range(10):
    squares.append(i ** 2)

# 列表推导式
squares = [i ** 2 for i in range(10)]
```

## 调试技巧

### 使用 print 调试

```python
print(f"Debug: variable = {variable}")
```

### 使用 logging 模块

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("信息日志")
logger.warning("警告日志")
logger.error("错误日志")
```

### 使用 pdb 调试器

```python
import pdb

def complex_function(x, y):
    pdb.set_trace()  # 设置断点
    result = x + y
    return result
```

## 总结

Python 是一种简单易学、功能强大的编程语言。掌握这些基础知识后，你可以：
- 开发 Web 应用（使用 Flask、Django）
- 进行数据分析（使用 Pandas、NumPy）
- 机器学习（使用 TensorFlow、PyTorch）
- 自动化脚本
- 科学计算

持续学习和实践是掌握 Python 的关键！
