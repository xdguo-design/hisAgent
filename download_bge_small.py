"""
BGE-small模型下载脚本 - 使用ModelScope
更小的模型，下载更快！
"""
import os
from modelscope import snapshot_download

def download_bge_small_model():
    """下载BGE-small-zh-v1.5模型（约100MB，速度快）"""

    model_dir = "models/bge-small-zh-v1.5"

    # 检查是否已下载
    if os.path.exists(model_dir):
        print(f"✅ 模型已存在于: {model_dir}")
        return model_dir

    print("🔍 开始从ModelScope下载BGE-small-zh-v1.5模型...")
    print("📦 模型大小约100MB，比BGE-base快4倍！")
    print("⚡ 速度和精度平衡，适合大多数场景")

    try:
        model_dir = snapshot_download(
            'Xorbits/bge-small-zh-v1.5',
            cache_dir='models',
            revision='master'
        )

        print(f"✅ 模型下载成功！")
        print(f"📁 模型保存位置: {model_dir}")

        return model_dir

    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return None

if __name__ == "__main__":
    download_bge_small_model()
