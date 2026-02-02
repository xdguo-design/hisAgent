"""
BGE模型下载脚本 - 使用ModelScope
"""
import os
from modelscope import snapshot_download

def download_bge_model():
    """下载BGE-base-zh-v1.5模型"""
    
    model_dir = os.path.join("models", "Xorbits", "bge-base-zh-v1___5")
    model_file = os.path.join(model_dir, "pytorch_model.bin")
    
    # 检查是否已下载完成
    if os.path.exists(model_file):
        print(f"✅ 模型已存在且完整: {model_dir}")
        return model_dir
    
    print("🔍 开始从ModelScope下载BGE-base-zh-v1.5模型...")
    print("📦 模型大小约400MB，请耐心等待...")
    
    try:
        model_dir = snapshot_download(
            'Xorbits/bge-base-zh-v1.5',
            cache_dir='models',
            revision='master'
        )
        
        print(f"✅ 模型下载成功！")
        print(f"📁 模型保存位置: {model_dir}")
        
        return model_dir
        
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        print("\n💡 提示：")
        print("1. 检查网络连接")
        print("2. 可以尝试使用智谱AI模型代替")
        return None

if __name__ == "__main__":
    download_bge_model()
