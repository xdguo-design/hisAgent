"""
FastAPI应用主入口

HIS开发Agent的RESTful API服务。
提供IDE（Trae、IDEA）调用的接口。
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
from pathlib import Path
from app.config import settings
from app.models.database import init_db, get_db
from app.api.routes import api_router
from app.core.prompt_manager import prompt_manager
from app.utils.logger import setup_logger, app_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    启动时执行初始化操作，关闭时执行清理操作。
    """
    # 启动时的初始化操作
    app_logger.info("=" * 50)
    app_logger.info("HIS开发Agent启动中...")
    app_logger.info("=" * 50)
    
    # 初始化数据库
    try:
        init_db()
        app_logger.info("数据库初始化完成")
    except Exception as e:
        app_logger.error(f"数据库初始化失败: {e}")
        raise
    
    # 初始化默认提示词模板
    try:
        db = next(get_db())
        try:
            prompt_manager.initialize_default_templates(db)
            app_logger.info("默认提示词模板初始化完成")
        finally:
            db.close()
    except Exception as e:
        app_logger.warning(f"默认提示词模板初始化失败: {e}")
    
    # 显示配置信息
    app_logger.info(f"API地址: http://{settings.api_host}:{settings.api_port}{settings.api_prefix}")
    app_logger.info(f"API文档: http://{settings.api_host}:{settings.api_port}/docs")
    app_logger.info("=" * 50)
    
    yield
    
    # 关闭时的清理操作
    app_logger.info("HIS开发Agent关闭中...")


# 创建FastAPI应用实例
app = FastAPI(
    title="HIS开发Agent API",
    description="基于智谱AI大模型的HIS系统开发智能助手，支持IDE（Trae、IDEA）调用。",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有HTTP请求"""
    import time
    start_time = time.time()
    
    # 记录请求信息
    app_logger.info(f"========== 请求开始 ==========")
    app_logger.info(f"方法: {request.method}")
    app_logger.info(f"路径: {request.url.path}")
    app_logger.info(f"查询参数: {request.url.query}")
    app_logger.info(f"客户端: {request.client.host if request.client else 'unknown'}")
    
    # 获取请求体（如果是文件上传，只记录元数据）
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            content_type = request.headers.get("content-type", "")
            if "multipart/form-data" in content_type:
                app_logger.info(f"内容类型: multipart/form-data (文件上传)")
            else:
                body = await request.body()
                app_logger.info(f"请求体大小: {len(body)} bytes")
        except Exception as e:
            app_logger.warning(f"无法读取请求体: {e}")
    
    # 处理请求
    response = await call_next(request)
    
    # 计算处理时间
    process_time = time.time() - start_time
    app_logger.info(f"状态码: {response.status_code}")
    app_logger.info(f"处理时间: {process_time:.3f}s")
    app_logger.info(f"========== 请求结束 ==========\n")
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    全局异常处理器
    
    捕获所有未处理的异常，返回统一的错误响应。
    """
    app_logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": f"服务器内部错误: {str(exc)}",
            "data": None
        }
    )


@app.get("/", tags=["根路径"])
async def root():
    """
    根路径
    
    返回前端管理页面。
    """
    frontend_file = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_file.exists():
        return FileResponse(str(frontend_file))
    return JSONResponse(
        status_code=404,
        content={"error": "管理页面未找到"}
    )


@app.get("/api/info", tags=["API信息"])
async def api_info():
    """
    API信息
    
    返回API基本信息。
    """
    return {
        "name": "HIS开发Agent API",
        "version": "1.0.0",
        "description": "基于智谱AI大模型的HIS系统开发智能助手",
        "docs": "/docs",
        "api_prefix": settings.api_prefix,
        "home": f"http://{settings.api_host}:{settings.api_port}/",
        "admin": f"http://{settings.api_host}:{settings.api_port}/"
    }


@app.get("/health", tags=["健康检查"])
async def health_check():
    """
    健康检查接口
    
    用于监控服务状态。
    """
    return {
        "status": "healthy",
        "service": "HIS开发Agent"
    }


# 注册API路由
app.include_router(api_router, prefix=settings.api_prefix)

# 挂载前端静态文件
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


@app.get("/index", tags=["管理界面"])
async def admin_page():
    """
    管理界面入口
    
    返回前端管理页面。
    """
    frontend_file = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_file.exists():
        return FileResponse(str(frontend_file))
    return JSONResponse(
        status_code=404,
        content={"error": "管理页面未找到"}
    )



def main():
    """
    主函数
    
    启动FastAPI服务器。
    """
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
