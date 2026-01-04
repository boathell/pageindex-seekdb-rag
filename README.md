# PageIndex + seekdb 混合RAG系统

> 结合结构化推理检索（PageIndex）和向量语义检索（seekdb）的新一代RAG系统

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## 🎯 项目简介

本项目创新性地将 **PageIndex的层次化推理检索** 与 **seekdb的向量语义检索** 相结合，打造了一个高精度、可解释的RAG系统。相比传统向量RAG，本系统具有：

- ✅ **更高的检索准确率** - 双路检索互补
- ✅ **更好的长文档理解** - 树结构导航
- ✅ **可解释的检索过程** - 基于推理路径
- ✅ **灵活的检索策略** - 支持tree-only/vector-only/hybrid三种模式
- ✅ **灵活的部署方式** - 支持Embedded本地存储和Docker服务器模式

## 🏗️ 系统架构

```
用户查询
    │
    ▼
混合检索引擎
    ├─→ PageIndex树检索 (结构化推理)
    │   └─→ BFS遍历章节树
    │
    └─→ seekdb向量检索 (语义匹配)
        └─→ AI原生混合搜索数据库
    │
    ▼
结果融合 (加权排序)
    │
    ▼
最终上下文
```

详细架构请参考：[architecture.md](architecture.md)

## 📦 快速开始

### 1. 环境要求

- Python 3.10+
- Docker & Docker Compose（Server模式）
- OpenAI API Key 或 阿里云 DashScope API Key（支持 Qwen-Max）

### 2. 启动 seekdb 数据库

**方式一：使用 Docker Compose（推荐）**

```bash
# 启动seekdb服务器
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f seekdb
```

**方式二：直接使用 Docker**

```bash
docker run -d \
  --name seekdb \
  -p 2881:2881 \
  -p 2886:2886 \
  -v ./data/seekdb:/var/lib/oceanbase \
  oceanbase/seekdb:latest
```

**方式三：使用 Embedded 模式（无需 Docker）**

如果不想使用 Docker，可以在 `.env` 文件中设置：
```
SEEKDB_MODE=embedded
```

### 3. 安装 Python 依赖

```bash
# 克隆项目
git clone https://github.com/yourusername/pageindex-seekdb-rag.git
cd pageindex-seekdb-rag

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
# 复制配置文件
cp .env.example .env

# 编辑配置文件，填入你的API Key
vim .env
```

**配置方式一：使用 OpenAI API**
```bash
# OpenAI 配置
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-2024-11-20
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# seekdb配置 - Server模式（使用Docker）
SEEKDB_MODE=server
SEEKDB_HOST=127.0.0.1
SEEKDB_PORT=2881
SEEKDB_DATABASE=rag_system
EMBEDDING_DIMS=1536
```

**配置方式二：使用 Qwen-Max API（阿里云 DashScope）**
```bash
# Qwen-Max 配置
API_KEY=your_dashscope_api_key_here
MODEL_NAME=qwen-max
BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_EMBEDDING_MODEL=text-embedding-v2

# PageIndex 配置
PAGEINDEX_MODEL=qwen-max

# seekdb配置
SEEKDB_MODE=server
SEEKDB_HOST=127.0.0.1
SEEKDB_PORT=2881
SEEKDB_DATABASE=rag_system
EMBEDDING_DIMS=1536
```

**配置方式三：使用 Embedded 模式（无需 Docker）**
```bash
# API 配置（OpenAI 或 Qwen-Max）
OPENAI_API_KEY=your_api_key_here

# seekdb Embedded 模式
SEEKDB_MODE=embedded
SEEKDB_PERSIST_DIR=./data/pyseekdb
EMBEDDING_DIMS=1536
```

### 5. 克隆PageIndex

```bash
# 创建外部依赖目录
mkdir -p external
cd external

# 克隆PageIndex项目
git clone https://github.com/VectifyAI/PageIndex.git
cd PageIndex
pip install -r requirements.txt

cd ../..
```

## 🚀 使用示例

### 示例0：启动 API 服务（推荐）

```bash
# 启动 API 服务
./start_api.sh

# 或手动启动
python -m uvicorn src.api_server:app --reload --host 0.0.0.0 --port 8000

# 访问 API 文档
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

**使用 API 进行索引和检索**:

```python
import requests

# 1. 索引文档
response = requests.post(
    "http://localhost:8000/index",
    json={
        "document_id": "my_doc",
        "pdf_path": "data/sample.pdf"
    }
)
print(response.json())

# 2. 检索
response = requests.post(
    "http://localhost:8000/search",
    json={
        "query": "文档的主要主题是什么？",
        "document_id": "my_doc",
        "strategy": "hybrid",
        "top_k": 5
    }
)
results = response.json()
for item in results['results']:
    print(f"Score: {item['score']:.4f}")
    print(f"Content: {item['content'][:200]}...")
```

详细的 API 文档请参考：[API文档](docs/api.md)

### 示例1：直接使用 Python SDK - 文档索引

```python
from src.document_indexer import DocumentIndexer
from src.config import config

# 创建索引器（使用配置文件中的seekdb设置）
indexer = DocumentIndexer(
    openai_api_key=config.openai.api_key,
    seekdb_mode=config.seekdb.mode,
    persist_directory=config.seekdb.persist_directory,
    seekdb_host=config.seekdb.host,
    seekdb_port=config.seekdb.port,
    seekdb_user=config.seekdb.user,
    seekdb_password=config.seekdb.password,
    seekdb_database=config.seekdb.database
)

# 索引PDF文档
result = indexer.index_document(
    pdf_path="data/sample.pdf",
    document_id="sample_001"
)

print(f"索引完成: {result['total_nodes']} 个节点, {result['total_chunks']} 个内容块")
```

### 示例2：混合检索

```python
from src.hybrid_search import HybridSearchEngine
from src.seekdb_manager import SeekDBManager
from src.embedding_manager import EmbeddingManager
from src.config import config

# 初始化seekdb管理器
db_manager = SeekDBManager(
    mode=config.seekdb.mode,
    persist_directory=config.seekdb.persist_directory,
    host=config.seekdb.host,
    port=config.seekdb.port,
    user=config.seekdb.user,
    password=config.seekdb.password,
    database=config.seekdb.database
)

embed_manager = EmbeddingManager(
    api_key=config.openai.api_key,
    model=config.openai.embedding_model
)

# 创建检索引擎
search_engine = HybridSearchEngine(
    seekdb_manager=db_manager,
    embedding_manager=embed_manager
)

# 执行检索
query = "文档的主要主题是什么？"
results = search_engine.hybrid_search(
    query=query,
    document_id="sample_001",
    strategy="hybrid"  # 可选: "tree_only", "vector_only", "hybrid"
)

# 输出结果
for i, result in enumerate(results[:5], 1):
    print(f"\n{i}. 分数: {result.score:.4f}")
    print(f"   路径: {' > '.join(result.node_path)}")
    print(f"   页码: {result.page_num}")
    print(f"   内容: {result.content[:200]}...")
```

### 示例3：三种检索策略对比

```python
# 策略1：仅树结构检索
tree_results = search_engine.hybrid_search(
    query=query,
    strategy="tree_only"
)

# 策略2：仅向量检索
vector_results = search_engine.hybrid_search(
    query=query,
    strategy="vector_only"
)

# 策略3：混合检索
hybrid_results = search_engine.hybrid_search(
    query=query,
    strategy="hybrid"
)

# 对比结果
print(f"Tree-only: {len(tree_results)} results")
print(f"Vector-only: {len(vector_results)} results")
print(f"Hybrid: {len(hybrid_results)} results")
```

## 📊 性能评测

我们在多个数据集上对比了不同RAG方案的性能：

| 方法 | Recall@5 | MRR | 平均延迟(ms) |
|------|----------|-----|-------------|
| 纯向量RAG | 0.65 | 0.58 | 120 |
| PageIndex | 0.72 | 0.68 | 350 |
| **Hybrid (Ours)** | **0.81** | **0.76** | **280** |

详细评测报告：[benchmark_results.md](data/results/benchmark_results.md)

## 🗂️ 项目结构

```
pageindex-seekdb-rag/
├── src/                        # 源代码
│   ├── config.py              # 配置管理
│   ├── pageindex_parser.py    # PageIndex集成
│   ├── seekdb_manager.py      # seekdb数据库管理
│   ├── embedding_manager.py   # Embedding向量化
│   ├── hybrid_search.py       # 混合检索引擎 (核心)
│   ├── document_indexer.py    # 文档索引器
│   └── api_server.py          # FastAPI服务
│
├── tests/                      # 测试代码
├── data/                       # 数据目录
│   ├── benchmark/             # 评测数据集
│   └── results/               # 评测结果
│
├── notebooks/                  # Jupyter notebooks
│   ├── demo.ipynb             # 系统演示
│   └── benchmark.ipynb        # 性能评测
│
├── configs/                    # 配置文件
├── docs/                       # 文档
├── external/                   # 外部依赖 (PageIndex)
├── requirements.txt            # Python依赖
├── .env.example               # 环境变量示例
└── README.md                  # 本文件
```

## 🔧 高级配置

### 调整检索权重

```python
from src.hybrid_search import HybridSearchConfig

config = HybridSearchConfig(
    tree_weight=0.4,      # 树检索权重
    vector_weight=0.6     # 向量检索权重
)

results = search_engine.hybrid_search(
    query=query,
    config=config
)
```

### 树搜索参数

```python
from src.hybrid_search import TreeSearchConfig

tree_config = TreeSearchConfig(
    max_depth=3,                  # 最大搜索深度
    top_k_per_level=5,            # 每层保留节点数
    similarity_threshold=0.6,     # 相似度阈值
    enable_pruning=True           # 启用剪枝
)
```

### 向量检索参数

```python
from src.hybrid_search import VectorSearchConfig

vector_config = VectorSearchConfig(
    top_k=20,             # 返回top-k结果
    enable_rerank=False   # 启用重排序
)
```

## ⚠️ 已知问题

### 1. Qwen Embedding API 批量限制
- **问题**: Qwen text-embedding-v2 API 单次最多支持 25 个文本
- **影响**: 大批量 embedding 时会自动分批，可能导致速度较慢
- **解决方案**: EmbeddingManager 已自动实现分批处理（batch_size=25）

### 2. 文档分块性能优化
- **问题**: 大型文档分块时可能耗时较长
- **状态**: 已识别，待优化
- **临时方案**: 适当调整 `chunk_size` 和 `chunk_overlap` 参数

### 3. PageIndex 输出格式兼容性
- **问题**: PageIndex 不同版本输出格式可能不同
- **解决方案**: PageIndexParser 已支持新旧两种格式自动识别

## 📝 更新日志

### v0.2.0 (2026-01-04)
- ✅ 支持 Qwen-Max API（阿里云 DashScope）
- ✅ 支持 seekdb Docker 服务器模式部署
- ✅ 修复向量维度配置（支持 1536 维 embedding）
- ✅ 优化 PageIndex 集成（支持新版输出格式）
- ✅ 改进配置管理（Pydantic Settings v2）

### v0.1.0 (2025-12-01)
- 🎉 初始版本发布
- ✅ PageIndex + seekdb 混合检索
- ✅ 支持三种检索策略
- ✅ seekdb Embedded 模式支持

## 📖 相关文档

- [技术架构](architecture.md) - 详细的系统设计文档
- [API文档](docs/api.md) - API接口说明
- [评测报告](docs/benchmark.md) - 性能评测详情
- [开发指南](docs/development.md) - 开发者指南

## 🤝 贡献指南

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md)

## 📄 开源协议

本项目采用 MIT 协议 - 详见 [LICENSE](LICENSE)

## 🙏 致谢

本项目基于以下优秀的开源项目：

- [PageIndex](https://github.com/VectifyAI/PageIndex) - 推理式RAG框架
- [seekdb](https://github.com/oceanbase/seekdb) - AI原生搜索数据库
- [OceanBase](https://github.com/oceanbase/oceanbase) - 分布式数据库

## 📮 联系方式

- 项目Issues: [GitHub Issues](https://github.com/yourusername/pageindex-seekdb-rag/issues)
- 邮箱: your.email@example.com

---

**如果这个项目对你有帮助，请给一个 ⭐️ Star！**
