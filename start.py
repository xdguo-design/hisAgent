"""
HIS开发Agent启动脚本

快速启动HIS开发Agent服务。
"""

import os
import sys
from pathlib import Path

def check_requirements():
    """检查必要的依赖和环境"""
    print("检查环境...")
    
    # 检查Python版本
    if sys.version_info < (3, 10):
        print("错误: 需要Python 3.10或更高版本")
        print(f"当前版本: {sys.version}")
        sys.exit(1)
    
    print(f"Python版本: {sys.version.split()[0]} [OK]")
    
    # 检查.env文件
    env_file = Path(".env")
    if not env_file.exists():
        print("\n警告: .env文件不存在")
        print("请从.env.example复制并配置:")
        print("  cp .env.example .env")
        print("  # 然后编辑.env文件，填入API密钥\n")
        
        # 尝试自动创建.env文件
        example_file = Path(".env.example")
        if example_file.exists():
            import shutil
            shutil.copy(example_file, env_file)
            print("已创建.env文件，请编辑并填入API密钥\n")
        else:
            print("错误: .env.example文件不存在")
            sys.exit(1)
    
    # 检查ZHIPUAI_API_KEY
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.getenv("ZHIPUAI_API_KEY"):
        print("警告: ZHIPUAI_API_KEY未设置")
        print("请在.env文件中设置智谱AI的API密钥\n")
    
    print("环境检查完成!\n")


def start_server():
    """启动FastAPI服务器"""
    print("=" * 60)
    print("HIS开发Agent")
    print("基于智谱AI大模型的HIS系统开发智能助手")
    print("=" * 60)
    print()
    
    # 检查环境
    check_requirements()
    
    # 导入并启动应用
    try:
        from app.main import main
        main()
    except ImportError as e:
        print(f"导入失败: {e}")
        print("请先安装依赖:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    start_server()
