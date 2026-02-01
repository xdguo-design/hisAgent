"""
AST 智能分块器

支持多种编程语言的基于抽象语法树的代码分块，包括：
- Java
- Python
- SQL
"""

import re
from typing import List, Dict, Optional
from llama_index.core import Document
from llama_index.core.schema import TextNode
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class ASTSplitter:
    """基于 AST 的代码分块器"""
    
    def __init__(self, max_chunk_size: int = 800):
        self.max_chunk_size = max_chunk_size
    
    def split_documents(
        self,
        documents: List[Document],
        chunk_size: int = None,
        chunk_overlap: int = None
    ) -> List[TextNode]:
        """
        分割文档列表
        
        Args:
            documents: 文档列表
            chunk_size: 最大块大小
            chunk_overlap: 重叠大小
        
        Returns:
            节点列表
        """
        if chunk_size:
            self.max_chunk_size = chunk_size
        
        all_nodes = []
        
        for doc in documents:
            nodes = self.split_single_document(doc)
            all_nodes.extend(nodes)
        
        logger.info(f"AST 分块完成，共生成 {len(all_nodes)} 个节点")
        return all_nodes
    
    def split_single_document(self, doc: Document) -> List[TextNode]:
        """
        分割单个文档
        
        Args:
            doc: 文档对象
        
        Returns:
            节点列表
        """
        text = doc.text
        file_path = doc.metadata.get('file_path', '')
        
        if not file_path:
            return self._fallback_split(doc)
        
        if file_path.endswith('.java'):
            return self._split_java_code(doc)
        elif file_path.endswith('.py'):
            return self._split_python_code(doc)
        elif file_path.endswith('.sql'):
            return self._split_sql_code(doc)
        else:
            return self._fallback_split(doc)
    
    def _split_java_code(self, doc: Document) -> List[TextNode]:
        """分割 Java 代码"""
        text = doc.text
        file_path = doc.metadata.get('file_path', '')
        
        try:
            nodes = []
            
            # 提取包和导入
            package = self._extract_java_package(text)
            imports = self._extract_java_imports(text)
            
            # 按类/接口/枚举分块
            pattern = r'(public|private|protected)?\s*(abstract|final|static)?\s*(class|interface|enum)\s+(\w+)'
            matches = list(re.finditer(pattern, text))
            
            for i, match in enumerate(matches):
                start = match.start()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                
                class_code = text[start:end]
                
                # 提取类信息
                class_name = match.group(4)
                type_name = match.group(3)
                
                # 提取方法签名
                method_signatures = self._extract_java_methods(class_code)
                
                # 构建节点内容
                node_content = self._build_java_chunk(
                    package, imports, class_code, class_name, type_name
                )
                
                # 创建节点
                metadata = {
                    'file_path': file_path,
                    'language': 'java',
                    'type': type_name,
                    'name': class_name,
                    'package': package,
                    'imports': imports,
                    'methods': method_signatures,
                    'chunk_type': 'ast_java_class'
                }
                
                node = TextNode(
                    text=node_content,
                    metadata={**doc.metadata, **metadata}
                )
                nodes.append(node)
            
            if not nodes:
                return self._fallback_split(doc)
            
            return nodes
            
        except Exception as e:
            logger.error(f"Java AST 分块失败: {e}")
            return self._fallback_split(doc)
    
    def _split_python_code(self, doc: Document) -> List[TextNode]:
        """分割 Python 代码"""
        text = doc.text
        file_path = doc.metadata.get('file_path', '')
        
        try:
            nodes = []
            
            # 按类/函数分块
            class_pattern = r'(class\s+(\w+)\s*(\([^)]*\))?\s*:|def\s+(\w+)\s*\([^)]*\)\s*(->[^:]+)?\s*:)'
            matches = list(re.finditer(class_pattern, text))
            
            if not matches:
                return self._fallback_split(doc)
            
            # 按模块分块（类或顶级函数）
            current_start = 0
            current_indent_level = 0
            
            for i, match in enumerate(matches):
                start = match.start()
                
                # 计算缩进级别
                line_start = text.rfind('\n', 0, start) + 1
                indent = len(text[line_start:start]) - len(text[line_start:start].lstrip())
                
                # 如果是顶级定义，创建新块
                if indent == 0:
                    if current_start < start:
                        module_code = text[current_start:start].strip()
                        if module_code:
                            node = TextNode(
                                text=module_code,
                                metadata={**doc.metadata, 'chunk_type': 'ast_python_module'}
                            )
                            nodes.append(node)
                    current_start = start
            
            # 添加最后一个块
            if current_start < len(text):
                module_code = text[current_start:].strip()
                if module_code:
                    node = TextNode(
                        text=module_code,
                        metadata={**doc.metadata, 'chunk_type': 'ast_python_module'}
                    )
                    nodes.append(node)
            
            if not nodes:
                return self._fallback_split(doc)
            
            return nodes
            
        except Exception as e:
            logger.error(f"Python AST 分块失败: {e}")
            return self._fallback_split(doc)
    
    def _split_sql_code(self, doc: Document) -> List[TextNode]:
        """分割 SQL 语句"""
        text = doc.text
        file_path = doc.metadata.get('file_path', '')
        
        try:
            nodes = []
            
            # 按语句分块（分号分隔）
            statements = [s.strip() for s in text.split(';') if s.strip()]
            
            for i, stmt in enumerate(statements):
                # 提取语句类型
                stmt_type = self._extract_sql_type(stmt)
                
                # 提取表名
                table_name = self._extract_sql_table_name(stmt)
                
                metadata = {
                    'file_path': file_path,
                    'language': 'sql',
                    'type': stmt_type,
                    'table': table_name,
                    'statement_index': i,
                    'chunk_type': 'ast_sql_statement'
                }
                
                node = TextNode(
                    text=stmt + ';',
                    metadata={**doc.metadata, **metadata}
                )
                nodes.append(node)
            
            if not nodes:
                return self._fallback_split(doc)
            
            return nodes
            
        except Exception as e:
            logger.error(f"SQL AST 分块失败: {e}")
            return self._fallback_split(doc)
    
    def _fallback_split(self, doc: Document) -> List[TextNode]:
        """默认分块方法"""
        from llama_index.core.node_parser import TextSplitter
        
        text = doc.text
        nodes = []
        
        # 按段落/函数/类简单分块
        chunks = []
        
        # 尝试按函数/类分块
        function_pattern = r'\n(def |class |public |private |protected |function |CREATE TABLE|SELECT |INSERT INTO|UPDATE |DELETE FROM)'
        matches = list(re.finditer(function_pattern, text))
        
        if matches:
            for i, match in enumerate(matches):
                start = match.start()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                chunk = text[start:end].strip()
                if chunk:
                    chunks.append(chunk)
        else:
            # 按段落分块
            chunks = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        # 创建节点
        for i, chunk in enumerate(chunks):
            metadata = {
                'chunk_type': 'fallback',
                'chunk_index': i
            }
            node = TextNode(
                text=chunk,
                metadata={**doc.metadata, **metadata}
            )
            nodes.append(node)
        
        return nodes
    
    def _extract_java_package(self, code: str) -> Optional[str]:
        """提取 Java 包名"""
        match = re.search(r'package\s+([\w.]+);', code)
        return match.group(1) if match else None
    
    def _extract_java_imports(self, code: str) -> List[str]:
        """提取 Java 导入语句"""
        return re.findall(r'import\s+([\w.*]+);', code)
    
    def _extract_java_methods(self, class_code: str) -> List[str]:
        """提取 Java 方法签名"""
        pattern = r'(public|private|protected|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\([^)]*\)'
        matches = re.findall(pattern, class_code)
        return [m[1] for m in matches]
    
    def _build_java_chunk(
        self,
        package: Optional[str],
        imports: List[str],
        class_code: str,
        class_name: str,
        type_name: str
    ) -> str:
        """构建 Java 块内容"""
        parts = []
        
        if package:
            parts.append(f'package {package};')
        
        # 限制导入数量
        for imp in imports[:10]:
            parts.append(f'import {imp};')
        
        if parts:
            parts.append('')
        
        parts.append(class_code)
        
        return '\n'.join(parts)
    
    def _extract_sql_type(self, stmt: str) -> str:
        """提取 SQL 语句类型"""
        stmt_upper = stmt.upper()
        if 'CREATE TABLE' in stmt_upper:
            return 'CREATE_TABLE'
        elif 'SELECT' in stmt_upper:
            return 'SELECT'
        elif 'INSERT' in stmt_upper:
            return 'INSERT'
        elif 'UPDATE' in stmt_upper:
            return 'UPDATE'
        elif 'DELETE' in stmt_upper:
            return 'DELETE'
        elif 'ALTER TABLE' in stmt_upper:
            return 'ALTER_TABLE'
        else:
            return 'UNKNOWN'
    
    def _extract_sql_table_name(self, stmt: str) -> Optional[str]:
        """提取 SQL 表名"""
        match = re.search(r'FROM\s+(\w+)|INTO\s+(\w+)|UPDATE\s+(\w+)|TABLE\s+(\w+)', stmt, re.IGNORECASE)
        if match:
            for group in match.groups():
                if group:
                    return group
        return None
