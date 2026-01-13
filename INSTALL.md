# 安装指南

本文档详细说明需要手动安装的组件和安装步骤。

## 一、Python环境要求

- **Python版本**：Python 3.8 或更高版本
- **推荐版本**：Python 3.9 - 3.11

### 检查Python版本
```bash
python --version
# 或
python3 --version
```

## 二、使用虚拟环境（强烈推荐）

### 为什么使用虚拟环境？

虚拟环境（venv）可以：
- **隔离依赖**：项目依赖不会污染全局Python环境
- **版本管理**：不同项目可以使用不同版本的包
- **易于部署**：可以轻松复制整个venv环境
- **团队协作**：确保团队成员使用相同的依赖版本
- **清理简单**：删除venv文件夹即可完全清理

### 创建虚拟环境

#### Windows:

1. 打开命令提示符（CMD）或PowerShell
2. 进入项目目录：
   ```bash
   cd D:\cursor\projects\knowledge-assistant
   ```
3. 运行设置脚本：
   ```bash
   setup_venv.bat
   ```

脚本会自动：
- 检查Python版本（需要3.8+）
- 创建`venv/`虚拟环境目录
- 激活虚拟环境并升级pip
- 安装`requirements.txt`中的所有依赖

#### Linux/macOS:

1. 打开终端
2. 进入项目目录：
   ```bash
   cd /path/to/knowledge-assistant
   ```
3. 给脚本添加执行权限并运行：
   ```bash
   chmod +x setup_venv.sh
   ./setup_venv.sh
   ```

### 激活虚拟环境

#### Windows:

**方式1：使用快捷脚本（推荐）**
```bash
activate.bat
```

**方式2：手动激活**
```bash
venv\Scripts\activate.bat
```

激活后，命令提示符前会显示`(venv)`。

#### Linux/macOS:

**方式1：使用快捷脚本（推荐）**
```bash
source activate.sh
```

**方式2：手动激活**
```bash
source venv/bin/activate
```

激活后，终端提示符前会显示`(venv)`。

### 退出虚拟环境

在任何平台，只需运行：
```bash
deactivate
```

### 运行应用

#### Windows:

**方式1：使用快捷脚本（推荐）**
```bash
run.bat
```

**方式2：手动激活后运行**
```bash
activate.bat
python run.py
```

#### Linux/macOS:

**方式1：使用快捷脚本（推荐）**
```bash
chmod +x run.sh
./run.sh
```

**方式2：手动激活后运行**
```bash
source activate.sh
python run.py
```

> **注意**：`run.bat`和`run.sh`脚本会自动检测并激活虚拟环境（如果未激活），所以可以直接运行。

### 不使用虚拟环境（不推荐）

如果你选择不使用虚拟环境，可以直接运行：
```bash
pip install -r requirements.txt
python run.py
```

但这种方式可能导致依赖冲突，特别是如果你有多个Python项目。

## 三、必须手动安装的组件

### 1. Ollama（本地大模型服务）

#### Windows安装：
1. 访问 https://ollama.ai/download
2. 下载Windows安装包
3. 运行安装程序
4. 安装完成后，Ollama会自动启动

#### 验证安装：
```bash
ollama --version
```

#### 拉取模型：
```bash
ollama pull <model_name>
```
常见模型：`llama2`, `mistral`, `qwen`, `deepseek-chat` 等

**注意**：首次拉取模型需要较长时间（模型大小约4-8GB），请确保网络连接稳定。

#### 启动Ollama服务：
```bash
ollama serve
```

默认服务地址：`http://localhost:11434`

### 2. Python依赖包

#### 使用虚拟环境安装（推荐）：

如果你已经创建了虚拟环境，依赖会在运行`setup_venv.bat`或`setup_venv.sh`时自动安装。

如果需要手动安装或更新依赖：

**Windows:**
```bash
activate.bat
pip install -r requirements.txt
```

**Linux/macOS:**
```bash
source activate.sh
pip install -r requirements.txt
```

#### 不使用虚拟环境安装（不推荐）：
```bash
cd knowledge-assistant
pip install -r requirements.txt
```

#### 主要依赖说明：

**核心依赖**：
- `aiohttp>=3.9.0` - 异步HTTP客户端
- `beautifulsoup4>=4.12.0` - HTML解析
- `lxml>=4.9.0` - XML/HTML解析器
- `pyyaml>=6.0` - YAML配置文件解析

**向量搜索依赖**：
- `sentence-transformers>=2.2.0` - 文本向量化模型
  - **首次运行会自动下载模型**（约400MB）
  - 模型名称：`paraphrase-multilingual-MiniLM-L12-v2`
  - 支持中文和多种语言
  
- `faiss-cpu>=1.7.4` - 向量搜索库（CPU版本）
  - Windows/Linux: 使用 `faiss-cpu`
  - 如果有NVIDIA GPU，可以安装 `faiss-gpu` 替代（性能更好）

#### 可选依赖（按需安装）：

**PDF文件支持**：
```bash
# 在激活的虚拟环境中运行
pip install PyPDF2 pdfplumber
```

**中文分词（如果需要更好的中文处理）**：
```bash
# 在激活的虚拟环境中运行
pip install jieba
```

**更现代的GUI（替代Tkinter）**：
```bash
# 在激活的虚拟环境中运行
# PyQt5
pip install PyQt5

# 或 PyQt6
pip install PyQt6
```

## 四、安装步骤总结

### 快速安装（推荐顺序）：

1. **安装Python**（如果未安装）
   ```bash
   # 从 https://www.python.org/downloads/ 下载安装
   # 确保版本 >= 3.8
   ```

2. **创建虚拟环境并安装依赖**
   
   **Windows:**
   ```bash
   cd D:\cursor\projects\knowledge-assistant
   setup_venv.bat
   ```
   
   **Linux/macOS:**
   ```bash
   cd /path/to/knowledge-assistant
   chmod +x setup_venv.sh
   ./setup_venv.sh
   ```

3. **安装Ollama**
   - 下载：https://ollama.ai/download
   - 安装并启动服务

4. **拉取Ollama模型**
   ```bash
   ollama pull <model_name>
   ```
   常见模型：`llama2`, `mistral`, `qwen`, `deepseek-chat` 等

5. **验证安装**
   ```bash
   # 检查Ollama
   ollama list
   
   # 检查Python包（在激活的虚拟环境中）
   # Windows: activate.bat
   # Linux/macOS: source activate.sh
   python -c "import aiohttp; import sentence_transformers; import faiss; print('所有依赖已安装')"
   ```

6. **启动应用**
   
   **Windows:**
   ```bash
   run.bat
   # 或
   activate.bat
   python run.py
   ```
   
   **Linux/macOS:**
   ```bash
   ./run.sh
   # 或
   source activate.sh
   python run.py
   ```

## 五、常见安装问题

### 问题1：pip安装失败（网络问题）

**解决方案**：
```bash
# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题2：faiss-cpu安装失败

**Windows解决方案**：
```bash
# 尝试使用conda安装
conda install -c conda-forge faiss-cpu

# 或使用预编译wheel文件
pip install https://github.com/facebookresearch/faiss/releases/download/v1.7.4/faiss-cpu-1.7.4-cp39-cp39-win_amd64.whl
```

### 问题3：sentence-transformers下载模型失败

**解决方案**：
- 确保网络连接正常
- 首次运行会自动下载，需要等待
- 如果下载失败，可以手动下载模型文件

### 问题4：Ollama连接失败

**检查清单**：
1. Ollama服务是否运行：`ollama list`
2. 端口是否被占用：检查11434端口
3. 防火墙是否阻止连接
4. config.yaml中的base_url配置是否正确

### 问题5：内存不足

**建议**：
- 向量模型需要约500MB-1GB内存
- Ollama + 模型需要2-8GB内存（取决于模型大小）
- 建议系统内存至少8GB

## 六、系统要求

### 最低配置：
- **CPU**：双核2.0GHz
- **内存**：4GB RAM
- **存储**：10GB可用空间
- **操作系统**：Windows 10/11, Linux, macOS

### 推荐配置：
- **CPU**：四核3.0GHz或更高
- **内存**：16GB RAM或更高
- **存储**：50GB可用空间（用于存储模型和数据库）
- **GPU**：NVIDIA GPU（可选，用于加速向量搜索和LLM推理）

## 七、验证安装

运行以下Python脚本验证所有组件：

**重要**：如果使用虚拟环境，请先激活虚拟环境再运行验证脚本。

**Windows:**
```bash
activate.bat
python test_installation.py
```

**Linux/macOS:**
```bash
source activate.sh
python test_installation.py
```

验证脚本内容：

```python
# test_installation.py
import sys

def check_import(module_name, package_name=None):
    try:
        __import__(module_name)
        print(f"✓ {package_name or module_name} 已安装")
        return True
    except ImportError:
        print(f"✗ {package_name or module_name} 未安装")
        return False

print("检查Python依赖...")
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
    if sys.prefix == sys.base_prefix:
        print("  提示: 未检测到虚拟环境，建议使用虚拟环境")
        print("  运行: setup_venv.bat (Windows) 或 ./setup_venv.sh (Linux/macOS)")
    else:
        print("  请运行: pip install -r requirements.txt")

# 检查Ollama连接
print("\n检查Ollama服务...")
try:
    import aiohttp
    import asyncio
    
    async def check_ollama():
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:11434/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status == 200:
                            print("✓ Ollama服务正在运行")
                            data = await resp.json()
                            models = [m['name'] for m in data.get('models', [])]
                            if models:
                                print(f"✓ 已安装 {len(models)} 个模型: {', '.join(models)}")
                            else:
                                print("✗ 未安装任何模型")
                                print("  请先安装Ollama模型，例如: ollama pull <model_name>")
                                return False
                        return True
        except:
            print("✗ 无法连接到Ollama服务")
            print("  请确保Ollama已安装并运行: ollama serve")
            return False
    
    asyncio.run(check_ollama())
except Exception as e:
    print(f"✗ 检查Ollama时出错: {e}")
```

保存为 `test_installation.py` 并运行：
```bash
python test_installation.py
```

## 八、下一步

安装完成后，请：
1. 查看 `README.md` 了解使用方法
2. 编辑 `config/config.yaml` 调整配置
3. 运行 `python run.py` 启动应用

祝使用愉快！

