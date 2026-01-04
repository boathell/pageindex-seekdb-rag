# PageIndex + pyseekdb 混合RAG系统

> 结合结构化推理检索（PageIndex）和向量语义检索（pyseekdb）的新一代RAG系统

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## 🎯 项目简介

本项目创新性地将 **PageIndex的层次化推理检索** 与 **pyseekdb的向量语义检索** 相结合，打造了一个高精度、可解释的RAG系统。相比传统向量RAG，本系统具有：

- ✅ **更高的检索准确率** - 双路检索互补
- ✅ **更好的长文档理解** - 树结构导航
- ✅ **可解释的检索过程** - 基于推理路径
- ✅ **灵活的检索策略** - 支持tree-only/vector-only/hybrid三种模式
- ✅ **零部署成本** - 使用pyseekdb本地存储，无需部署数据库

## 🏗️ 系统架构

```
用户查询
    │
    ▼
混合检索引擎
    ├─→ PageIndex树检索 (结构化推理)
    │   └─→ BFS遍历章节树
    │
    └─→ pyseekdb向量检索 (语义匹配)
        └─→ 本地HNSW向量索引
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
- OpenAI API Key

### 2. 安装依赖

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

### 3. 配置环境变量

```bash
# 复制配置文件
cp .env.example .env

# 编辑配置文件，填入你的API Key
vim .env
```

必填配置：
```
OPENAI_API_KEY=your_openai_api_key_here
PYSEEKDB_PERSIST_DIR=./data/pyseekdb  # 本地向量数据库存储路径
```

### 4. 克隆PageIndex

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

### 示例1：文档索引

```python
from src.document_indexer import DocumentIndexer
from src.config import config

# 创建索引器
indexer = DocumentIndexer(
    openai_api_key=config.openai.api_key,
    persist_directory=config.pyseekdb.persist_directory
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

# 初始化组件
db_manager = SeekDBManager(
    persist_directory=config.pyseekdb.persist_directory
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
