# 个人知识库助手 (Knowledge Assistant)

一个基于Python + SQLite构建的个人知识库系统，集成本地大模型（Ollama），支持网页抓取、文件索引和智能问答。

## 功能特性

- ✅ **网页内容抓取**：异步批量抓取网页内容并存储到数据库
- ✅ **文件索引**：支持多种文件格式的索引，自动提取内容
- ✅ **增量索引**：智能检测文件变化，只索引新增或修改的文件
- ✅ **向量搜索**：基于sentence-transformers和FAISS的语义搜索
- ✅ **智能问答**：结合本地大模型，基于知识库回答问题
- ✅ **GUI界面**：友好的图形界面，操作简单直观

## 项目结构

```
knowledge-assistant/
├── backend/                 # 后端服务
│   ├── database/           # 数据库模型和管理
│   ├── services/           # 核心服务（抓取、索引、搜索、LLM）
│   └── utils/              # 工具模块（配置管理）
├── client/                 # 客户端
│   └── gui/                # GUI客户端
├── data/                   # 数据目录
│   ├── knowledge_base.db   # SQLite数据库
│   ├── faiss_index.bin     # FAISS索引文件
│   └── faiss_metadata.pkl  # FAISS元数据
├── config/                 # 配置文件
│   └── config.yaml         # 主配置文件
├── venv/                   # 虚拟环境（运行setup_venv后生成）
├── setup_venv.bat          # Windows虚拟环境设置脚本
├── setup_venv.sh           # Linux/macOS虚拟环境设置脚本
├── activate.bat            # Windows激活脚本
├── activate.sh             # Linux/macOS激活脚本
├── run.bat                 # Windows运行脚本
├── run.sh                  # Linux/macOS运行脚本
├── run.py                  # 应用启动脚本
├── requirements.txt        # Python依赖
└── README.md              # 项目说明
```

## 安装步骤

### 1. 创建虚拟环境（推荐）

使用虚拟环境可以隔离项目依赖，避免污染全局Python环境。

**Windows:**
```bash
setup_venv.bat
```

**Linux/macOS:**
```bash
chmod +x setup_venv.sh
./setup_venv.sh
```

脚本会自动：
- 检查Python版本（需要3.8+）
- 创建venv虚拟环境
- 安装所有项目依赖

### 2. 安装Ollama和模型

1. 下载并安装Ollama：https://ollama.ai/
2. 拉取你需要的模型（例如）：
```bash
ollama pull <model_name>
```
常见模型：`llama2`, `mistral`, `qwen`, `deepseek-chat` 等

### 3. 启动Ollama服务

确保Ollama服务正在运行（默认端口11434）：
```bash
ollama serve
```

### 4. 配置项目

编辑 `config/config.yaml` 文件，根据你的实际情况调整配置：
- Ollama服务地址（默认：http://localhost:11434）
- 模型名称（可在config.yaml中配置）
- 数据库路径
- 向量模型（默认使用多语言模型）

## 使用方法

### 启动GUI客户端

**方式1：使用快捷脚本（推荐）**

**Windows:**
```bash
run.bat
```

**Linux/macOS:**
```bash
chmod +x run.sh
./run.sh
```

**方式2：手动激活虚拟环境**

**Windows:**
```bash
activate.bat
python run.py
```

**Linux/macOS:**
```bash
source activate.sh
python run.py
```

**方式3：直接运行（如果已激活venv）**
```bash
python run.py
```

> **注意**：如果未使用虚拟环境，可以直接运行 `python run.py`，但建议使用虚拟环境以避免依赖冲突。

### 功能说明

#### 1. 网页抓取
- 输入URL，点击"抓取"按钮
- 支持批量抓取多个URL
- 自动提取网页标题和正文内容
- 生成向量嵌入并存储

#### 2. 文件索引
- 选择单个文件或整个目录进行索引
- 支持增量索引，只处理新增或修改的文件
- 自动识别文件类型，提取文本内容
- 生成向量嵌入并存储

#### 3. 智能问答
- 输入问题，系统会自动搜索相关知识库
- 结合搜索结果调用本地大模型生成回答
- 显示参考来源，便于追溯

## 技术架构

### 后端技术栈
- **Python 3.8+**：主要编程语言
- **SQLite**：轻量级数据库
- **aiohttp**：异步HTTP客户端
- **BeautifulSoup**：HTML解析
- **sentence-transformers**：文本向量化
- **FAISS**：高效向量搜索

### 前端技术栈
- **Tkinter**：Python内置GUI框架

### 大模型集成
- **Ollama**：本地大模型服务
- 支持任何Ollama兼容的模型

## 性能优化

1. **异步处理**：使用aiohttp实现异步网页抓取，提高并发性能
2. **向量搜索**：使用FAISS实现高效的相似度搜索
3. **增量索引**：通过内容哈希检测文件变化，避免重复索引
4. **数据库索引**：在关键字段上创建索引，加速查询

## 配置说明

### config.yaml 主要配置项

```yaml
database:
  path: "data/knowledge_base.db"  # 数据库路径

ollama:
  base_url: "http://localhost:11434"  # Ollama服务地址
  model_name: "deepseek-chat"          # 模型名称（可修改为任何已安装的模型）
  timeout: 120                          # 请求超时时间

scraper:
  timeout: 10           # 网页抓取超时
  max_concurrent: 5     # 最大并发数

file_indexer:
  supported_extensions: [".txt", ".md", ".py", ...]  # 支持的文件类型
  check_interval: 60    # 增量检查间隔（秒）

vector_search:
  model_name: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
  embedding_dim: 384    # 向量维度
  top_k: 5              # 搜索结果数量
```

## 注意事项

1. **首次运行**：向量模型会自动下载（约400MB），需要网络连接
2. **内存占用**：向量模型加载后约占用500MB-1GB内存
3. **数据库大小**：建议定期清理不需要的数据，避免数据库过大
4. **Ollama服务**：确保Ollama服务正常运行，否则问答功能不可用

## 常见问题

### Q: 向量搜索功能不可用？
A: 确保已安装sentence-transformers和faiss-cpu，首次运行会自动下载模型。

### Q: 无法连接到Ollama服务？
A: 检查Ollama是否运行，以及config.yaml中的base_url配置是否正确。

### Q: 文件索引失败？
A: 检查文件编码，系统会自动尝试多种编码，但某些二进制文件可能无法索引。

### Q: 如何提高搜索准确性？
A: 可以尝试使用更大的向量模型，或调整top_k参数增加搜索结果数量。

## 后续优化方向

- [ ] 支持更多文件格式（PDF、Word、Excel等）
- [ ] 添加Web界面
- [ ] 支持多用户
- [ ] 添加数据导出功能
- [ ] 支持自定义向量模型
- [ ] 添加数据可视化

## 许可证

MIT License

## 作者

个人知识库助手项目

