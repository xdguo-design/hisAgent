"""
PDF 文档加载器
提供对 PDF 文件的解析支持
"""

from llama_index.core import Document
from typing import List
import os


class PDFReader:
    """PDF 文档读取器"""
    
    def load_data(self, file_path: str) -> List[Document]:
        """
        从 PDF 文件加载文本内容
        
        Args:
            file_path: PDF 文件路径
            
        Returns:
            Document 对象列表
        """
        try:
            # 尝试使用 pdfplumber（效果更好）
            return self._load_with_pdfplumber(file_path)
        except Exception as e:
            print(f"pdfplumber 加载失败: {e}，尝试使用 PyPDF2")
            try:
                return self._load_with_pypdf2(file_path)
            except Exception as e2:
                print(f"PyPDF2 加载也失败: {e2}")
                raise
    
    def _load_with_pdfplumber(self, file_path: str) -> List[Document]:
        """使用 pdfplumber 加载 PDF"""
        import pdfplumber
        
        documents = []
        file_name = os.path.basename(file_path)
        
        with pdfplumber.open(file_path) as pdf:
            text_content = []
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text and text.strip():
                    text_content.append(f"--- 第 {page_num} 页 ---\n{text}")
            
            full_text = "\n\n".join(text_content)
            if full_text.strip():
                documents.append(Document(
                    text=full_text,
                    metadata={
                        "file_name": file_name,
                        "file_path": file_path,
                        "file_type": "pdf",
                        "page_count": len(pdf.pages)
                    }
                ))
        
        return documents
    
    def _load_with_pypdf2(self, file_path: str) -> List[Document]:
        """使用 PyPDF2 加载 PDF（备用方案）"""
        from PyPDF2 import PdfReader
        
        documents = []
        file_name = os.path.basename(file_path)
        
        reader = PdfReader(file_path)
        text_content = []
        
        for page_num, page in enumerate(reader.pages, 1):
            text = page.extract_text()
            if text and text.strip():
                text_content.append(f"--- 第 {page_num} 页 ---\n{text}")
        
        full_text = "\n\n".join(text_content)
        if full_text.strip():
            documents.append(Document(
                text=full_text,
                metadata={
                    "file_name": file_name,
                    "file_path": file_path,
                    "file_type": "pdf",
                    "page_count": len(reader.pages)
                }
            ))
        
        return documents


def load_pdf_files(file_paths: List[str]) -> List[Document]:
    """
    批量加载 PDF 文件
    
    Args:
        file_paths: PDF 文件路径列表
        
    Returns:
        Document 对象列表
    """
    reader = PDFReader()
    documents = []
    
    for file_path in file_paths:
        try:
            docs = reader.load_data(file_path)
            documents.extend(docs)
            print(f"✅ 成功加载 PDF: {os.path.basename(file_path)} (共 {len(docs)} 个文档)")
        except Exception as e:
            print(f"❌ 加载 PDF 失败 {file_path}: {e}")
    
    return documents
