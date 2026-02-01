"""
路由注册模块

统一注册所有API路由。
"""

from fastapi import APIRouter
from app.api import llm, knowledge, prompt, his, document_generator, admin

# 创建主路由
api_router = APIRouter()

# 注册子路由
api_router.include_router(llm.router)
api_router.include_router(knowledge.router)
api_router.include_router(prompt.router)
api_router.include_router(his.router)
api_router.include_router(document_generator.router)
api_router.include_router(admin.router)
