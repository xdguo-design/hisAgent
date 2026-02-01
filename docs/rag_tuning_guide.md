# Java 代码知识库分块策略指南

## 目录
1. [Java 代码分块核心原则](#java-代码分块核心原则)
2. [分块粒度选择](#分块粒度选择)
3. [基础分块配置](#基础分块配置)
4. [高级分块策略](#高级分块策略)
5. [元数据保留策略](#元数据保留策略)
6. [不同场景的分块方案](#不同场景的分块方案)
7. [代码示例](#代码示例)
8. [常见问题与解决方案](#常见问题与解决方案)

---

## Java 代码分块核心原则

### 1. 语义完整性优先
- **类级完整性**：每个 chunk 应包含完整的类声明或方法实现
- **上下文保留**：保留包名、导入语句、类级注释等关键信息
- **逻辑边界**：按 Java 语法结构切分（类、方法、字段、代码块）

### 2. Java 语法结构特点
```
包声明 (package)
    ↓
导入语句 (import) 
    ↓
类/接口/枚举声明 (class/interface/enum)
    ↓
字段声明 (fields)
    ↓
构造方法 (constructors)
    ↓
方法定义 (methods)
    ↓
内部类 (inner classes)
```

### 3. 分块决策树
```
┌─────────────────────────────────────────────────────────────┐
│                    Java 代码分块决策树                         │
├─────────────────────────────────────────────────────────────┤
│  代码类型?                                                    │
│    ├─ API/库代码 → 方法级分块 (保留完整签名+注释)              │
│    ├─ 业务逻辑代码 → 类级分块 (保留上下文)                     │
│    ├─ 工具类 → 方法级分块 (高复用性)                          │
│    └─ 框架/配置 → 文件级分块 (保留整体结构)                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 分块粒度选择

### 粒度对比表

| 粒度 | chunk_size | 适用场景 | 优点 | 缺点 |
|------|-----------|----------|------|------|
| **方法级** | 200-500 | API查询、工具类 | 精准匹配、高复用 | 丢失类上下文 |
| **类级** | 800-2000 | 业务逻辑、框架 | 完整上下文 | 检索噪声大 |
| **混合级** | 500-1000 | 通用场景 | 平衡精准和上下文 | 配置复杂 |
| **逻辑单元** | 300-800 | 复杂算法 | 语义完整 | 需自定义规则 |

### 推荐配置

#### 方案 A：方法级分块（推荐）
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter, Language

# Java 方法级分块
java_method_splitter = RecursiveCharacterTextSplitter.from_language(
    language=Language.JAVA,
    chunk_size=600,
    chunk_overlap=100,
    separators=[
        "\n  public ",      # 方法分隔（2空格缩进）
        "\n  private ",     
        "\n  protected ",
        "\n  static ",
        "\n\n",            # 空行
        "\n",              # 换行
        ";",               # 语句结束
        " "
    ]
)
```

#### 方案 B：类级分块
```python
# Java 类级分块
java_class_splitter = RecursiveCharacterTextSplitter.from_language(
    language=Language.JAVA,
    chunk_size=1500,
    chunk_overlap=200,
    separators=[
        "\npublic class ",      # 类分隔
        "\nclass ",
        "\ninterface ",
        "\nenum ",
        "\n@",                  # 注解分隔
        "\n\n",
        "\n"
    ]
)
```

#### 方案 C：智能混合分块
```python
# 基于代码密度的动态分块
def get_java_splitter(code_type: str):
    """根据代码类型返回合适的分块器"""
    configs = {
        "api": {
            "chunk_size": 400,
            "separators": ["\n  public ", "\n  private ", "\n\n"]
        },
        "service": {
            "chunk_size": 1000,
            "separators": ["\npublic class ", "\n\n", "\n  public "]
        },
        "util": {
            "chunk_size": 500,
            "separators": ["\n  public static ", "\n  private static ", "\n\n"]
        }
    }
    config = configs.get(code_type, configs["service"])
    return RecursiveCharacterTextSplitter.from_language(
        language=Language.JAVA,
        chunk_size=config["chunk_size"],
        chunk_overlap=config["chunk_size"] // 10,
        separators=config["separators"]
    )
```

---

## 基础分块配置

### 1. 标准 Java 分块器

```python
from langchain.text_splitter import Language, RecursiveCharacterTextSplitter
from typing import List, Dict

class JavaCodeSplitter:
    """Java 代码专用分块器"""
    
    def __init__(self, strategy="method"):
        self.strategy = strategy
        self.splitter = self._create_splitter()
    
    def _create_splitter(self):
        if self.strategy == "method":
            return RecursiveCharacterTextSplitter.from_language(
                language=Language.JAVA,
                chunk_size=512,
                chunk_overlap=50,
                separators=[
                    "\n    public ",     # 4空格缩进方法
                    "\n    private ",
                    "\n    protected ",
                    "\n  public ",      # 2空格缩进
                    "\n  private ",
                    "\n  protected ",
                    "\n\n",
                    "\n",
                    ". "
                ]
            )
        elif self.strategy == "class":
            return RecursiveCharacterTextSplitter.from_language(
                language=Language.JAVA,
                chunk_size=1024,
                chunk_overlap=100,
                separators=[
                    "\npublic class ",
                    "\nclass ",
                    "\ninterface ",
                    "\nenum ",
                    "\nabstract class ",
                    "\n\n"
                ]
            )
        else:  # mixed
            return RecursiveCharacterTextSplitter.from_language(
                language=Language.JAVA,
                chunk_size=768,
                chunk_overlap=80,
                separators=[
                    "\n    public ",
                    "\n    private ",
                    "\n    @",           # 注解
                    "\n  @",
                    "\n\n",
                    "\n"
                ]
            )
    
    def split(self, code: str) -> List[Dict]:
        """分块并保留元数据"""
        chunks = self.splitter.create_documents([code])
        enriched_chunks = []
        
        for i, chunk in enumerate(chunks):
            enriched = self._enrich_chunk(chunk, code, i)
            enriched_chunks.append(enriched)
        
        return enriched_chunks
    
    def _enrich_chunk(self, chunk, full_code, index):
        """为 chunk 添加 Java 特定的元数据"""
        content = chunk.page_content
        
        # 提取类名
        class_name = self._extract_class_name(content, full_code)
        
        # 提取方法签名
        method_sig = self._extract_method_signature(content)
        
        # 提取包名
        package = self._extract_package(full_code)
        
        # 提取导入语句
        imports = self._extract_imports(full_code)
        
        return {
            "content": content,
            "metadata": {
                "index": index,
                "class_name": class_name,
                "method_signature": method_sig,
                "package": package,
                "imports": imports[:5],  # 最多保留5个相关导入
                "chunk_type": self._get_chunk_type(content),
                "line_count": content.count('\n')
            }
        }
    
    def _extract_class_name(self, content, full_code):
        """提取类名"""
        import re
        # 从内容或完整代码中提取
        class_match = re.search(r'class\s+(\w+)', content)
        if class_match:
            return class_match.group(1)
        
        # 从完整代码中提取第一个类名
        class_match = re.search(r'class\s+(\w+)', full_code)
        return class_match.group(1) if class_match else "Unknown"
    
    def _extract_method_signature(self, content):
        """提取方法签名"""
        import re
        # 匹配方法声明
        method_pattern = r'(public|private|protected|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\([^)]*\)'
        match = re.search(method_pattern, content)
        if match:
            return match.group(0)
        return None
    
    def _extract_package(self, code):
        """提取包名"""
        import re
        match = re.search(r'package\s+([\w.]+);', code)
        return match.group(1) if match else None
    
    def _extract_imports(self, code):
        """提取导入语句"""
        import re
        imports = re.findall(r'import\s+([\w.*]+);', code)
        return imports
    
    def _get_chunk_type(self, content):
        """判断 chunk 类型"""
        if "class " in content or "interface " in content:
            return "class_definition"
        elif any(x in content for x in ["public ", "private ", "protected "]):
            return "method"
        elif "@" in content:
            return "annotation"
        else:
            return "code_block"


# 使用示例
splitter = JavaCodeSplitter(strategy="method")

java_code = '''
package com.example.service;

import java.util.List;
import java.util.ArrayList;
import org.springframework.stereotype.Service;

/**
 * 用户服务类
 */
@Service
public class UserService {
    
    private UserRepository userRepository;
    
    public UserService(UserRepository repository) {
        this.userRepository = repository;
    }
    
    /**
     * 根据ID查询用户
     */
    public User findById(Long id) {
        return userRepository.findById(id).orElse(null);
    }
    
    /**
     * 保存用户
     */
    public User saveUser(User user) {
        return userRepository.save(user);
    }
}
'''

chunks = splitter.split(java_code)
for chunk in chunks:
    print(f"Type: {chunk['metadata']['chunk_type']}")
    print(f"Class: {chunk['metadata']['class_name']}")
    print(f"Method: {chunk['metadata']['method_signature']}")
    print(f"Content preview: {chunk['content'][:100]}...")
    print("-" * 50)
```

---

## 高级分块策略

### 1. 基于 AST 的智能分块

```python
import javalang
from typing import List, Dict, Tuple

class ASTBasedJavaSplitter:
    """基于抽象语法树的 Java 分块器"""
    
    def __init__(self, max_chunk_size=800):
        self.max_chunk_size = max_chunk_size
    
    def split(self, code: str) -> List[Dict]:
        """基于 AST 进行语义分块"""
        try:
            tree = javalang.parse.parse(code)
        except:
            # 解析失败回退到文本分块
            return self._fallback_split(code)
        
        chunks = []
        package = None
        imports = []
        
        # 提取包和导入
        for path, node in tree:
            if isinstance(node, javalang.tree.PackageDeclaration):
                package = node.name
            elif isinstance(node, javalang.tree.Import):
                imports.append(node.path)
        
        # 按类分块
        for type_decl in tree.types:
            class_chunk = self._process_class(type_decl, code, package, imports)
            if class_chunk:
                chunks.append(class_chunk)
        
        return chunks
    
    def _process_class(self, type_decl, code: str, package: str, imports: List[str]) -> Dict:
        """处理类声明"""
        class_name = type_decl.name
        
        # 提取类注释
        class_doc = self._extract_documentation(type_decl)
        
        # 提取字段
        fields = []
        for field in type_decl.fields:
            field_info = {
                "name": field.declarators[0].name if field.declarators else "unknown",
                "type": field.type.name if field.type else "unknown",
                "modifiers": [str(m) for m in field.modifiers]
            }
            fields.append(field_info)
        
        # 提取方法
        methods = []
        for method in type_decl.methods:
            method_info = {
                "name": method.name,
                "signature": self._get_method_signature(method),
                "documentation": self._extract_documentation(method),
                "modifiers": [str(m) for m in method.modifiers]
            }
            methods.append(method_info)
        
        # 构建 chunk 内容
        content = self._build_class_content(
            class_name, class_doc, fields, methods, code
        )
        
        return {
            "content": content,
            "metadata": {
                "type": "class",
                "name": class_name,
                "package": package,
                "imports": imports,
                "fields": fields,
                "methods": [m["name"] for m in methods],
                "documentation": class_doc
            }
        }
    
    def _get_method_signature(self, method) -> str:
        """获取方法签名"""
        modifiers = ' '.join([str(m) for m in method.modifiers])
        return_type = method.return_type.name if method.return_type else "void"
        name = method.name
        params = ', '.join([f"{p.type.name} {p.name}" for p in method.parameters])
        return f"{modifiers} {return_type} {name}({params})"
    
    def _extract_documentation(self, node) -> str:
        """提取 Javadoc 注释"""
        # javalang 支持提取注释
        if hasattr(node, 'documentation') and node.documentation:
            return node.documentation
        return ""
    
    def _build_class_content(self, class_name, doc, fields, methods, code):
        """构建类的文本内容"""
        lines = [f"Class: {class_name}"]
        
        if doc:
            lines.append(f"Documentation: {doc}")
        
        if fields:
            lines.append("Fields:")
            for f in fields:
                lines.append(f"  - {f['name']}: {f['type']}")
        
        if methods:
            lines.append("Methods:")
            for m in methods:
                lines.append(f"  - {m['signature']}")
                if m['documentation']:
                    lines.append(f"    Doc: {m['documentation']}")
        
        return '\n'.join(lines)
    
    def _fallback_split(self, code: str) -> List[Dict]:
        """回退到简单分块"""
        # 使用 LangChain 作为后备
        from langchain.text_splitter import RecursiveCharacterTextSplitter, Language
        
        splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.JAVA,
            chunk_size=self.max_chunk_size,
            chunk_overlap=100
        )
        
        docs = splitter.create_documents([code])
        return [{"content": d.page_content, "metadata": {"type": "fallback"}} for d in docs]


# 使用示例
ast_splitter = ASTBasedJavaSplitter(max_chunk_size=1000)
```

### 2. 语义感知分块

```python
class SemanticJavaSplitter:
    """基于语义的 Java 代码分块"""
    
    def __init__(self):
        self.semantic_boundaries = [
            "public class ",
            "public interface ",
            "public enum ",
            "public abstract class ",
            "public static class ",
            "private class ",
            "protected class ",
        ]
    
    def split_by_semantics(self, code: str) -> List[Dict]:
        """按语义边界分块"""
        import re
        
        chunks = []
        
        # 1. 提取文件级信息
        package = self._extract_package(code)
        imports = self._extract_imports(code)
        
        # 2. 按顶层类型分块
        # 匹配类、接口、枚举定义
        pattern = r'(public|private|protected)?\s*(abstract|final|static)?\s*(class|interface|enum)\s+(\w+)'
        
        matches = list(re.finditer(pattern, code))
        
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(code)
            
            class_code = code[start:end]
            
            # 构建带上下文的 chunk
            chunk_content = self._build_contextual_chunk(
                package, imports, class_code
            )
            
            chunks.append({
                "content": chunk_content,
                "metadata": {
                    "type": match.group(3),  # class/interface/enum
                    "name": match.group(4),
                    "modifiers": [m for m in [match.group(1), match.group(2)] if m],
                    "package": package,
                    "has_javadoc": self._has_javadoc(class_code)
                }
            })
        
        return chunks
    
    def _build_contextual_chunk(self, package, imports, class_code):
        """构建带上下文的 chunk"""
        parts = []
        
        if package:
            parts.append(f"package {package};")
        
        # 只保留与类相关的导入（简单启发式：包含类中使用的类型）
        relevant_imports = self._filter_relevant_imports(imports, class_code)
        for imp in relevant_imports[:10]:  # 限制导入数量
            parts.append(f"import {imp};")
        
        parts.append("")
        parts.append(class_code)
        
        return '\n'.join(parts)
    
    def _filter_relevant_imports(self, imports, class_code):
        """过滤相关的导入语句"""
        # 简单启发式：导入路径中的类名是否出现在代码中
        relevant = []
        for imp in imports:
            class_name = imp.split('.')[-1]
            if class_name in class_code and class_name != '*':
                relevant.append(imp)
        return relevant
    
    def _has_javadoc(self, code):
        """检查是否有 Javadoc 注释"""
        return '/**' in code or '@author' in code or '@param' in code


# 使用示例
semantic_splitter = SemanticJavaSplitter()
```

---

## 元数据保留策略

### 1. 必须保留的元数据

```python
JAVA_METADATA_SCHEMA = {
    # 文件级元数据
    "file_path": "文件的完整路径",
    "package": "包名，如 com.example.service",
    "imports": "导入的类列表",
    "file_type": "文件类型：class/interface/enum/annotation",
    
    # 类级元数据
    "class_name": "类名",
    "class_modifiers": "类修饰符：[public, abstract, final]",
    "extends": "父类",
    "implements": "实现的接口列表",
    "class_documentation": "类级 Javadoc",
    "annotations": "类上的注解，如 @Service @Entity",
    
    # 方法级元数据
    "method_name": "方法名",
    "method_signature": "完整方法签名",
    "method_modifiers": "方法修饰符",
    "return_type": "返回类型",
    "parameters": "参数列表",
    "method_documentation": "方法 Javadoc",
    "throws": "抛出的异常",
    
    # 代码特征
    "line_count": "代码行数",
    "complexity": "圈复杂度（可选）",
    "is_test": "是否为测试代码",
    "is_deprecated": "是否已弃用"
}
```

### 2. 元数据提取器

```python
import re
from typing import Dict, List, Optional

class JavaMetadataExtractor:
    """Java 代码元数据提取器"""
    
    @staticmethod
    def extract_all(code: str, file_path: str = None) -> Dict:
        """提取所有元数据"""
        return {
            **JavaMetadataExtractor.extract_file_metadata(code, file_path),
            **JavaMetadataExtractor.extract_class_metadata(code),
            **JavaMetadataExtractor.extract_method_metadata(code)
        }
    
    @staticmethod
    def extract_file_metadata(code: str, file_path: str = None) -> Dict:
        """提取文件级元数据"""
        return {
            "file_path": file_path,
            "package": JavaMetadataExtractor._extract_package(code),
            "imports": JavaMetadataExtractor._extract_imports(code),
            "import_count": len(JavaMetadataExtractor._extract_imports(code))
        }
    
    @staticmethod
    def extract_class_metadata(code: str) -> Dict:
        """提取类级元数据"""
        class_pattern = r'(public|private|protected)?\s*(abstract|final)?\s*class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?'
        match = re.search(class_pattern, code)
        
        if not match:
            return {}
        
        return {
            "class_name": match.group(3),
            "class_modifiers": [m for m in [match.group(1), match.group(2)] if m],
            "extends": match.group(4),
            "implements": [i.strip() for i in match.group(5).split(',')] if match.group(5) else [],
            "annotations": JavaMetadataExtractor._extract_class_annotations(code),
            "class_documentation": JavaMetadataExtractor._extract_class_javadoc(code)
        }
    
    @staticmethod
    def extract_method_metadata(code: str) -> Dict:
        """提取方法级元数据"""
        methods = []
        
        # 匹配方法定义
        method_pattern = r'(@[\w\(]+\s+)*(public|private|protected|static|\s)+([\w<>\[\]]+)\s+(\w+)\s*\(([^)]*)\)'
        
        for match in re.finditer(method_pattern, code):
            annotations = re.findall(r'@(\w+)', match.group(0))
            
            methods.append({
                "method_signature": match.group(0),
                "method_name": match.group(4),
                "return_type": match.group(3),
                "modifiers": match.group(2).split(),
                "parameters": JavaMetadataExtractor._parse_parameters(match.group(5)),
                "annotations": annotations
            })
        
        return {
            "methods": methods,
            "method_count": len(methods)
        }
    
    @staticmethod
    def _extract_package(code: str) -> Optional[str]:
        match = re.search(r'package\s+([\w.]+);', code)
        return match.group(1) if match else None
    
    @staticmethod
    def _extract_imports(code: str) -> List[str]:
        return re.findall(r'import\s+([\w.*]+);', code)
    
    @staticmethod
    def _extract_class_annotations(code: str) -> List[str]:
        # 提取类声明前的注解
        class_pos = re.search(r'(public|private|protected)?\s*class', code)
        if not class_pos:
            return []
        
        before_class = code[:class_pos.start()]
        return re.findall(r'@(\w+)', before_class)
    
    @staticmethod
    def _extract_class_javadoc(code: str) -> Optional[str]:
        # 提取类前的 Javadoc
        match = re.search(r'/\*\*(.*?)\*/\s*(?=\n\s*(public|private|protected)?\s*class)', code, re.DOTALL)
        return match.group(1).strip() if match else None
    
    @staticmethod
    def _parse_parameters(params_str: str) -> List[Dict]:
        """解析参数列表"""
        if not params_str.strip():
            return []
        
        params = []
        for param in params_str.split(','):
            param = param.strip()
            if param:
                parts = param.split()
                if len(parts) >= 2:
                    params.append({
                        "type": ' '.join(parts[:-1]),
                        "name": parts[-1]
                    })
        return params


# 使用示例
metadata = JavaMetadataExtractor.extract_all(java_code, "UserService.java")
print(metadata)
```

---

## 不同场景的分块方案

### 场景 1：Spring Boot API 文档

```python
def split_spring_api(code: str) -> List[Dict]:
    """Spring Boot API 代码分块 - 注重方法级精度"""
    
    splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.JAVA,
        chunk_size=400,
        chunk_overlap=50,
        separators=[
            "\n    @",           # 注解分隔
            "\n    public ",      # 公共方法
            "\n    @GetMapping",
            "\n    @PostMapping",
            "\n    @PutMapping",
            "\n    @DeleteMapping",
            "\n    @RequestMapping",
        ]
    )
    
    docs = splitter.create_documents([code])
    
    enriched = []
    for doc in docs:
        # 提取 API 元数据
        endpoint = extract_api_endpoint(doc.page_content)
        http_method = extract_http_method(doc.page_content)
        
        enriched.append({
            "content": doc.page_content,
            "metadata": {
                "type": "api_endpoint",
                "endpoint": endpoint,
                "http_method": http_method,
                "has_swagger": "@Api" in doc.page_content or "@Operation" in doc.page_content
            }
        })
    
    return enriched


def extract_api_endpoint(content: str) -> str:
    """提取 API 端点路径"""
    import re
    patterns = [
        r'@GetMapping\(["\']([^"\']+)["\']\)',
        r'@PostMapping\(["\']([^"\']+)["\']\)',
        r'@RequestMapping\(["\']([^"\']+)["\']\)',
    ]
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1)
    return None


def extract_http_method(content: str) -> str:
    """提取 HTTP 方法"""
    if "@GetMapping" in content:
        return "GET"
    elif "@PostMapping" in content:
        return "POST"
    elif "@PutMapping" in content:
        return "PUT"
    elif "@DeleteMapping" in content:
        return "DELETE"
    return "UNKNOWN"
```

### 场景 2：领域模型（Entity/POJO）

```python
def split_domain_model(code: str) -> List[Dict]:
    """领域模型分块 - 保留完整类和字段关系"""
    
    # 对领域模型使用更大的 chunk_size，保留上下文
    splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.JAVA,
        chunk_size=1200,      # 更大的块
        chunk_overlap=100,
        separators=[
            "\n@Entity",
            "\n@Table",
            "\npublic class",
            "\n    private ",     # 字段分隔（备选）
            "\n\n"
        ]
    )
    
    docs = splitter.create_documents([code])
    
    # 增强实体类元数据
    enriched = []
    for doc in docs:
        metadata = {
            "type": "entity",
            "is_entity": "@Entity" in doc.page_content,
            "table_name": extract_table_name(doc.page_content),
            "fields": extract_field_names(doc.page_content),
            "has_relations": any(x in doc.page_content for x in ["@OneToMany", "@ManyToOne", "@OneToOne"])
        }
        
        enriched.append({
            "content": doc.page_content,
            "metadata": metadata
        })
    
    return enriched


def extract_table_name(content: str) -> str:
    """提取表名"""
    import re
    match = re.search(r'@Table\(name\s*=\s*["\']([^"\']+)["\']\)', content)
    if match:
        return match.group(1)
    # 从类名推断
    class_match = re.search(r'class\s+(\w+)', content)
    return class_match.group(1) if class_match else None


def extract_field_names(content: str) -> List[str]:
    """提取字段名"""
    import re
    return re.findall(r'private\s+[\w<>\[\]]+\s+(\w+);', content)
```

### 场景 3：工具类

```python
def split_utility_class(code: str) -> List[Dict]:
    """工具类分块 - 方法级，强调静态方法"""
    
    # 工具类通常由独立静态方法组成，适合细粒度分块
    splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.JAVA,
        chunk_size=300,       # 小粒度
        chunk_overlap=30,
        separators=[
            "\n    public static ",
            "\n    private static ",
            "\n    public final static ",
            "\n  public static ",
            "\n  private static ",
        ]
    )
    
    docs = splitter.create_documents([code])
    
    enriched = []
    for doc in docs:
        method_name = extract_static_method_name(doc.page_content)
        
        enriched.append({
            "content": doc.page_content,
            "metadata": {
                "type": "utility_method",
                "method_name": method_name,
                "is_static": "static" in doc.page_content,
                "is_public": "public" in doc.page_content
            }
        })
    
    return enriched


def extract_static_method_name(content: str) -> str:
    """提取静态方法名"""
    import re
    match = re.search(r'static\s+[\w<>\[\]]+\s+(\w+)\s*\(', content)
    return match.group(1) if match else None
```

---

## 代码示例

### 完整使用示例

```python
# 完整的 Java RAG 系统示例

from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
import os

class JavaRAGSystem:
    def __init__(self, strategy="method"):
        self.splitter = JavaCodeSplitter(strategy=strategy)
        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-large-zh-v1.5",
            encode_kwargs={"normalize_embeddings": True}
        )
        self.vectorstore = None
    
    def ingest_code(self, java_files: List[str]):
        """批量导入 Java 代码"""
        all_chunks = []
        
        for file_path in java_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # 分块
            chunks = self.splitter.split(code)
            
            # 添加文件路径
            for chunk in chunks:
                chunk['metadata']['source_file'] = file_path
                chunk['metadata']['file_name'] = os.path.basename(file_path)
            
            all_chunks.extend(chunks)
        
        # 存入向量库
        texts = [c['content'] for c in all_chunks]
        metadatas = [c['metadata'] for c in all_chunks]
        
        self.vectorstore = Chroma.from_texts(
            texts=texts,
            embedding=self.embeddings,
            metadatas=metadatas,
            collection_name="java_code_kb"
        )
        
        return len(all_chunks)
    
    def query(self, question: str, k=5) -> List[Dict]:
        """查询代码库"""
        if not self.vectorstore:
            raise ValueError("请先导入代码")
        
        results = self.vectorstore.similarity_search_with_score(question, k=k)
        
        formatted_results = []
        for doc, score in results:
            formatted_results.append({
                "code": doc.page_content,
                "metadata": doc.metadata,
                "relevance_score": score
            })
        
        return formatted_results


# 使用示例
if __name__ == "__main__":
    # 初始化系统
    rag = JavaRAGSystem(strategy="method")
    
    # 导入代码
    java_files = [
        "src/main/java/com/example/UserService.java",
        "src/main/java/com/example/OrderService.java",
    ]
    chunk_count = rag.ingest_code(java_files)
    print(f"已导入 {chunk_count} 个代码块")
    
    # 查询
    results = rag.query("如何根据用户ID查询用户信息？", k=3)
    for r in results:
        print(f"\n相关度: {r['relevance_score']:.3f}")
        print(f"类名: {r['metadata']['class_name']}")
        print(f"方法: {r['metadata']['method_signature']}")
        print(f"代码:\n{r['code'][:300]}...")
```

---

## 常见问题与解决方案

### 1. 内部类处理

```python
def handle_inner_classes(code: str) -> List[Dict]:
    """处理内部类 - 将内部类作为独立 chunk"""
    import re
    
    # 匹配内部类
    inner_class_pattern = r'(public|private|protected)?\s*class\s+(\w+)\s*\{'
    
    chunks = []
    outer_class = extract_outer_class(code)
    
    # 先提取外部类
    outer_match = re.search(r'public\s+class\s+(\w+)', code)
    if outer_match:
        outer_end = find_matching_brace(code, outer_match.end() - 1)
        outer_code = code[:outer_end]
        
        chunks.append({
            "content": outer_code,
            "metadata": {
                "type": "outer_class",
                "name": outer_match.group(1),
                "is_inner": False
            }
        })
    
    # 提取内部类
    for match in re.finditer(inner_class_pattern, code):
        if match.start() > 0 and code[match.start()-1] != '\n':
            # 可能是内部类
            inner_name = match.group(2)
            inner_start = match.start()
            inner_end = find_matching_brace(code, match.end() - 1)
            
            inner_code = code[inner_start:inner_end]
            
            # 添加上下文
            contextual_code = f"// 外部类: {outer_class}\n{inner_code}"
            
            chunks.append({
                "content": contextual_code,
                "metadata": {
                    "type": "inner_class",
                    "name": inner_name,
                    "outer_class": outer_class,
                    "is_inner": True
                }
            })
    
    return chunks


def find_matching_brace(code: str, open_pos: int) -> int:
    """找到匹配的右大括号"""
    count = 1
    pos = open_pos + 1
    while count > 0 and pos < len(code):
        if code[pos] == '{':
            count += 1
        elif code[pos] == '}':
            count -= 1
        pos += 1
    return pos


def extract_outer_class(code: str) -> str:
    """提取外部类名"""
    import re
    match = re.search(r'public\s+class\s+(\w+)', code)
    return match.group(1) if match else "Unknown"
```

### 2. Lambda 表达式处理

```python
def handle_lambda_expressions(code: str) -> str:
    """处理 Lambda 表达式 - 避免在 Lambda 内部分块"""
    import re
    
    # Lambda 表达式模式
    lambda_pattern = r'\([^)]*\)\s*->\s*\{[^}]*\}'
    
    # 将 Lambda 表达式替换为占位符，防止被切分
    placeholder = "/* LAMBDA_EXPRESSION */"
    processed_code = re.sub(lambda_pattern, placeholder, code)
    
    return processed_code
```

### 3. 泛型处理

```python
def preserve_generics(code: str) -> str:
    """保留泛型信息 - 避免泛型符号被误切"""
    import re
    
    # 识别泛型声明并保护
    generic_pattern = r'<[^>]+>'
    
    def protect_generics(match):
        generic = match.group(0)
        # 替换空格为特殊标记，防止被分隔符切分
        return generic.replace(' ', '___SPACE___')
    
    protected = re.sub(generic_pattern, protect_generics, code)
    return protected


def restore_generics(code: str) -> str:
    """恢复泛型信息"""
    return code.replace('___SPACE___', ' ')
```

### 4. 分块后处理

```python
def post_process_chunks(chunks: List[Dict]) -> List[Dict]:
    """分块后处理 - 过滤、合并、优化"""
    processed = []
    
    for chunk in chunks:
        content = chunk['content']
        
        # 1. 过滤过小的块（少于 50 字符）
        if len(content) < 50:
            continue
        
        # 2. 过滤纯注释块（可选）
        if is_pure_comment(content):
            continue
        
        # 3. 恢复泛型
        content = restore_generics(content)
        
        # 4. 格式化代码
        content = format_code(content)
        
        chunk['content'] = content
        processed.append(chunk)
    
    return processed


def is_pure_comment(content: str) -> bool:
    """检查是否为纯注释"""
    lines = content.strip().split('\n')
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('//') and not stripped.startswith('/*') and not stripped.startswith('*'):
            return False
    return True


def format_code(content: str) -> str:
    """简单格式化代码"""
    # 移除多余空行
    lines = content.split('\n')
    formatted = []
    prev_empty = False
    
    for line in lines:
        stripped = line.strip()
        if stripped == '':
            if not prev_empty:
                formatted.append(line)
            prev_empty = True
        else:
            formatted.append(line)
            prev_empty = False
    
    return '\n'.join(formatted)
```

### 5. 性能优化

```python
import hashlib
from functools import lru_cache

class OptimizedJavaSplitter:
    """带缓存的 Java 分块器"""
    
    def __init__(self, strategy="method"):
        self.strategy = strategy
        self.splitter = self._create_splitter()
        self._cache = {}
    
    def split_with_cache(self, code: str, file_path: str = None) -> List[Dict]:
        """带缓存的分块"""
        # 计算代码哈希
        code_hash = hashlib.md5(code.encode()).hexdigest()
        cache_key = f"{code_hash}_{self.strategy}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # 执行分块
        result = self._do_split(code, file_path)
        
        # 缓存结果
        self._cache[cache_key] = result
        
        return result
    
    def _do_split(self, code, file_path):
        """实际分块逻辑"""
        # 使用 JavaCodeSplitter
        splitter = JavaCodeSplitter(strategy=self.strategy)
        return splitter.split(code)


# 并行处理多个文件
from concurrent.futures import ThreadPoolExecutor

def process_files_parallel(files: List[str], max_workers=4) -> List[Dict]:
    """并行处理多个 Java 文件"""
    splitter = OptimizedJavaSplitter(strategy="method")
    
    def process_single(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        return splitter.split_with_cache(code, file_path)
    
    all_chunks = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(process_single, files)
        for chunks in results:
            all_chunks.extend(chunks)
    
    return all_chunks
```

---

## 总结：Java 分块速查表

| 场景 | 推荐策略 | chunk_size | 关键分隔符 | 元数据重点 |
|------|---------|-----------|-----------|-----------|
| **API/Controller** | 方法级 | 400-600 | `@GetMapping`, `public ResponseEntity` | endpoint, HTTP方法 |
| **Service 业务** | 方法级 | 500-800 | `public User`, `private void` | 事务注解, 参数类型 |
| **Entity/POJO** | 类级 | 1000-1500 | `@Entity`, `public class` | 表名, 字段映射 |
| **Util 工具类** | 方法级 | 300-500 | `public static`, `private static` | 方法名, 是否静态 |
| **复杂算法** | 逻辑单元 | 600-1000 | 自定义函数边界 | 算法名称, 复杂度 |
| **框架配置** | 类级 | 1200-2000 | `@Configuration`, `class` | 配置类型, Bean名称 |

**最佳实践口诀：**
- API 代码：注解驱动，方法级切分
- 业务代码：类为主体，保留上下文
- 工具方法：独立成块，强调复用
- 领域模型：类级完整，关系清晰