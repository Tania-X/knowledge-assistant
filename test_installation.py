"""安装验证脚本"""
import sys

def check_import(module_name, package_name=None):
    """检查模块是否已安装"""
    try:
        __import__(module_name)
        print(f"✓ {package_name or module_name} 已安装")
        return True
    except ImportError:
        print(f"✗ {package_name or module_name} 未安装")
        return False

def main():
    print("=" * 60)
    print("知识库助手 - 安装验证")
    print("=" * 60)
    
    print("\n【1/2】检查Python依赖...")
    checks = [
        check_import("aiohttp"),
        check_import("bs4", "beautifulsoup4"),
        check_import("lxml"),
        check_import("yaml", "pyyaml"),
        check_import("sentence_transformers", "sentence-transformers"),
        check_import("faiss"),
    ]
    
    if all(checks):
        print("\n✓ 所有Python依赖已安装")
    else:
        print("\n✗ 部分依赖未安装")
        print("  请运行: pip install -r requirements.txt")
    
    print("\n【2/2】检查Ollama服务...")
    try:
        import aiohttp
        import asyncio
        
        async def check_ollama():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "http://localhost:11434/api/tags", 
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as resp:
                        if resp.status == 200:
                            print("✓ Ollama服务正在运行")
                            data = await resp.json()
                            models = [m['name'] for m in data.get('models', [])]
                            if 'deepseek-chat' in models:
                                print("✓ DeepSeek模型已安装")
                            else:
                                print("✗ DeepSeek模型未安装")
                                print("  请运行: ollama pull deepseek-chat")
                            return True
            except Exception as e:
                print(f"✗ 无法连接到Ollama服务: {e}")
                print("  请确保Ollama已安装并运行: ollama serve")
                return False
        
        asyncio.run(check_ollama())
    except Exception as e:
        print(f"✗ 检查Ollama时出错: {e}")
    
    print("\n" + "=" * 60)
    print("验证完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()

