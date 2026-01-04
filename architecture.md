# PageIndex + pyseekdb 混合RAG系统技术架构文档

## 1. 项目概述

### 1.1 项目目标
构建一个结合**结构化推理检索**（PageIndex）和**向量语义检索**（pyseekdb）的新一代RAG系统，实现：
- 更高的检索准确率
- 更好的长文档理解能力
- 可解释的检索过程
- 零部署成本（使用本地向量数据库）

### 1.2 核心创新点
1. **双路检索融合**：树结构导航 + 向量语义匹配
2. **分层索引**：章节级粗检索 → 段落级精检索
3. **可解释性**：基于推理路径的检索过程

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     混合检索引擎                              │
│  (RAG Orchestrator)                                         │
│  ┌──────────────┐        ┌─────────────────┐               │
│  │  Query       │───────▶│  Route Strategy │               │
│  │  Analyzer    │        │  Selector       │               │
│  └──────────────┘        └─────────────────┘               │
└───────┬─────────────────────────┬───────────────────────────┘
        │                         │
        ▼                         ▼
┌──────────────────┐      ┌──────────────────┐
│  PageIndex       │      │  pyseekdb Vector │
│  Tree Search     │      │  Search          │
│  (结构化检索)     │      │  (语义检索)       │
└────────┬─────────┘      └────────┬─────────┘
         │                         │
         └────────┬────────────────┘
                  ▼
         ┌────────────────┐
         │  Result Merger │
         │  (结果融合)     │
         └────────┬───────┘
                  │
                  ▼
         ┌────────────────┐
         │   pyseekdb     │
         │   本地存储      │
         │ (向量+元数据)   │
         └────────────────┘
```

### 2.2 数据流设计

```
[PDF文档] 
    │
    ├─▶ [PageIndex解析] ──▶ 生成树结构JSON
    │                        │
    │                        ▼
    │                   [树节点提取]
    │                   - node_id
    │                   - title
    │                   - summary
    │                   - start_page/end_page
    │                   - level (层级)
    │                        │
    └─▶ [文本提取] ──────────┼─▶ [Embedding] ──▶ 向量
                             │
                             ▼
                   ┌─────────────────────────┐
                   │   pyseekdb 本地存储    │
                   ├─────────────────────────┤
                   │ collections:            │
                   │                         │
                   │ 1. tree_nodes           │
                   │    - id (node_id)       │
                   │    - document (summary) │
                   │    - embedding (vec)    │
                   │    - metadata:          │
                   │      * parent_id        │
                   │      * title            │
                   │      * level            │
                   │      * page_range       │
                   │                         │
                   │ 2. content_chunks       │
                   │    - id (chunk_id)      │
                   │    - document (content) │
                   │    - embedding (vec)    │
                   │    - metadata:          │
                   │      * node_id          │
                   │      * page_num         │
                   └─────────────────────────┘
```

### 2.3 检索流程

```
[用户查询]
    │
    ▼
[Query分析]
    │
    ├─▶ 查询类型判断
    │   - 概述性问题 → 侧重树检索
    │   - 细节性问题 → 侧重向量检索
    │   - 混合问题   → 双路并行
    │
    ▼
┌───────────────────────────────────────┐
│        并行检索阶段                    │
├───────────────────────────────────────┤
│                                       │
│  Path 1: 树结构检索                   │
│  ┌─────────────────────────────┐     │
│  │ 1. 根节点语义匹配            │     │
│  │ 2. BFS/DFS遍历子节点         │     │
│  │ 3. 剪枝策略(相似度阈值)      │     │
│  │ 4. 返回相关章节node_id列表   │     │
│  └─────────────────────────────┘     │
│           │                           │
│           └─────────┐                 │
│                     ▼                 │
│  Path 2: 向量检索                     │
│  ┌─────────────────────────────┐     │
│  │ 1. Query Embedding           │     │
│  │ 2. seekdb混合检索:           │     │
│  │    - 向量相似度搜索          │     │
│  │    - 全文关键词匹配          │     │
│  │ 3. 返回top-k chunks          │     │
│  └─────────────────────────────┘     │
│           │                           │
└───────────┼───────────────────────────┘
            │
            ▼
    ┌───────────────┐
    │  结果融合策略  │
    ├───────────────┤
    │ 1. 树路径加权 │
    │    - 层级越深, │
    │      相关性越高│
    │                │
    │ 2. 向量分数归一│
    │                │
    │ 3. 混合排序:   │
    │   score = α·   │
    │   tree_score + │
    │   β·vec_score  │
    │                │
    │ 4. 去重合并    │
    └───────┬───────┘
            │
            ▼
    [最终上下文]
            │
            ▼
    [LLM生成答案]
```

---

## 3. 技术栈

### 3.1 核心组件

| 组件 | 技术选型 | 版本 | 用途 |
|------|----------|------|------|
| 文档解析 | PageIndex | latest | 树结构生成 |
| 向量数据库 | pyseekdb | latest | 本地向量+元数据存储 |
| Embedding | OpenAI/Qwen | text-embedding-3-small | 文本向量化 |
| LLM | GPT-4/Qwen-Max | - | 最终答案生成 |
| 编排工具 | Dify | latest | 工作流编排 |
| Python | 3.10+ | - | 后端开发 |

### 3.2 依赖库

```python
# requirements.txt
pyseekdb>=0.1.0
openai>=1.0.0
langchain>=0.1.0
numpy>=1.24.0
pydantic>=2.0.0
fastapi>=0.100.0
uvicorn>=0.23.0
python-dotenv>=1.0.0
```

---

## 4. 数据库设计

### 4.1 seekdb Collection Schema

#### Collection 1: tree_nodes
```python
{
    "name": "document_tree_nodes",
    "schema": {
        "node_id": "string",          # 节点ID (如 "0001", "0001.1")
        "parent_id": "string",         # 父节点ID
        "document_id": "string",       # 所属文档ID
        "title": "string",             # 节点标题
        "summary": "text",             # 节点摘要
        "summary_vector": "vector",    # 摘要向量 (1536维)
        "level": "int",                # 层级深度
        "start_page": "int",           # 起始页码
        "end_page": "int",             # 结束页码
        "child_count": "int",          # 子节点数量
        "metadata": "json"             # 其他元数据
    },
    "indexes": {
        "vector_index": {
            "field": "summary_vector",
            "type": "HNSW",
            "metric": "cosine"
        },
        "tree_index": ["parent_id", "level"]
    }
}
```

#### Collection 2: content_chunks
```python
{
    "name": "document_chunks",
    "schema": {
        "chunk_id": "string",          # 块ID
        "node_id": "string",           # 所属节点ID (外键)
        "document_id": "string",       # 所属文档ID
        "content": "text",             # 文本内容
        "content_vector": "vector",    # 内容向量
        "page_num": "int",             # 页码
        "chunk_index": "int",          # 在节点内的序号
        "word_count": "int",           # 字数
        "metadata": "json"
    },
    "indexes": {
        "vector_index": {
            "field": "content_vector",
            "type": "HNSW",
            "metric": "cosine"
        },
        "full_text_index": ["content"],
        "foreign_key": ["node_id"]
    }
}
```

---

## 5. 核心算法

### 5.1 树结构检索算法

```python
def tree_search(query_embedding, max_depth=3, top_k=5):
    """
    基于推理的树搜索算法
    
    Args:
        query_embedding: 查询向量
        max_depth: 最大搜索深度
        top_k: 每层保留的top节点数
    
    Returns:
        relevant_nodes: 相关节点列表
    """
    
    # 1. 根节点匹配
    root_nodes = seekdb.query(
        collection="tree_nodes",
        vector=query_embedding,
        filter={"level": 0},
        limit=top_k
    )
    
    relevant_nodes = []
    queue = [(node, 1) for node in root_nodes]  # (node, depth)
    
    # 2. BFS遍历
    while queue:
        current_node, depth = queue.pop(0)
        
        # 相似度阈值剪枝
        if current_node.similarity < 0.6:
            continue
            
        relevant_nodes.append(current_node)
        
        # 深度限制
        if depth >= max_depth:
            continue
        
        # 3. 获取子节点并排序
        children = seekdb.query(
            collection="tree_nodes",
            vector=query_embedding,
            filter={"parent_id": current_node.node_id},
            limit=top_k
        )
        
        # 加入队列
        queue.extend([(child, depth+1) for child in children])
    
    return relevant_nodes
```

### 5.2 混合检索融合算法

```python
def hybrid_search(query, alpha=0.4, beta=0.6):
    """
    混合检索策略
    
    Args:
        query: 用户查询
        alpha: 树检索权重
        beta: 向量检索权重
    
    Returns:
        final_context: 融合后的上下文
    """
    
    query_embedding = embed(query)
    
    # 1. 树检索
    tree_results = tree_search(query_embedding)
    tree_node_ids = [node.node_id for node in tree_results]
    
    # 2. 向量检索
    vector_results = seekdb.hybrid_query(
        collection="content_chunks",
        vector=query_embedding,
        text_query=query,
        limit=20
    )
    
    # 3. 分数归一化
    tree_scores = normalize_scores([n.similarity for n in tree_results])
    vector_scores = normalize_scores([c.similarity for c in vector_results])
    
    # 4. 融合策略
    merged_results = {}
    
    # 树结果加权
    for i, node in enumerate(tree_results):
        # 获取该节点下的所有chunks
        chunks = seekdb.query(
            collection="content_chunks",
            filter={"node_id": node.node_id}
        )
        for chunk in chunks:
            chunk_id = chunk.chunk_id
            # 层级越深，分数越高
            tree_bonus = (node.level + 1) * 0.1
            score = alpha * (tree_scores[i] + tree_bonus)
            
            if chunk_id not in merged_results:
                merged_results[chunk_id] = {
                    "chunk": chunk,
                    "score": score,
                    "from_tree": True
                }
            else:
                merged_results[chunk_id]["score"] += score
    
    # 向量结果加权
    for i, chunk in enumerate(vector_results):
        chunk_id = chunk.chunk_id
        score = beta * vector_scores[i]
        
        if chunk_id not in merged_results:
            merged_results[chunk_id] = {
                "chunk": chunk,
                "score": score,
                "from_vector": True
            }
        else:
            merged_results[chunk_id]["score"] += score
            merged_results[chunk_id]["from_vector"] = True
    
    # 5. 排序并返回top结果
    sorted_results = sorted(
        merged_results.values(),
        key=lambda x: x["score"],
        reverse=True
    )[:10]
    
    # 6. 构建最终上下文
    final_context = build_context(sorted_results, tree_node_ids)
    
    return final_context
```

---

## 6. Python客户端使用方式

### 6.1 文档索引

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
    document_id="doc_001",
    metadata={"title": "Sample Document"}
)

print(f"索引完成: {result['total_nodes']} 节点, {result['total_chunks']} 内容块")
```

### 6.2 混合检索

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
results = search_engine.hybrid_search(
    query="文档的主要主题是什么？",
    document_id="doc_001",
    strategy="hybrid"  # "tree_only", "vector_only", "hybrid"
)

# 输出结果
for i, result in enumerate(results[:5], 1):
    print(f"\n{i}. 分数: {result.score:.4f}")
    print(f"   路径: {' > '.join(result.node_path)}")
    print(f"   内容: {result.content[:200]}...")
```

---

## 7. 性能优化策略

### 7.1 索引优化
- **向量索引**：使用HNSW算法，M=16, efConstruction=200
- **缓存策略**（使用pyseekdb存储）：
  - 树结构缓存：缓存解析后的文档树，避免重复解析
  - 查询结果缓存：缓存检索结果（15分钟TTL）
  - Embedding缓存：使用Python内置`functools.lru_cache`

### 7.2 检索优化
- **Early Stopping**：树搜索相似度阈值剪枝
- **并行检索**：树检索和向量检索并发执行
- **批处理**：批量Embedding生成

### 7.3 可扩展性
- **分片存储**：按文档分Collection
- **异步处理**：文档索引异步任务队列
- **负载均衡**：seekdb集群部署

---

## 8. 评测指标

### 8.1 准确率指标
- **Recall@K**：前K个结果的召回率
- **MRR (Mean Reciprocal Rank)**：平均倒数排名
- **NDCG (Normalized Discounted Cumulative Gain)**：归一化折损累积增益

### 8.2 效率指标
- **检索延迟**：平均检索时间 (ms)
- **索引时间**：文档索引速度 (pages/sec)
- **存储成本**：每文档存储大小 (MB)

### 8.3 对比基准
- **Baseline 1**：纯向量RAG (Langchain + FAISS)
- **Baseline 2**：纯树检索 (PageIndex only)
- **Baseline 3**：传统全文检索 (Elasticsearch)

---

## 9. 部署架构

### 9.1 开发环境
```
本地开发（Python客户端模式）:
- Python 3.10+ 虚拟环境
- pyseekdb本地存储 (./data/pyseekdb)
- 直接调用 Python 模块进行索引和检索
- Jupyter Notebook 用于交互式开发和评测
```

### 9.2 生产环境（未来扩展）
```
如需对外提供服务，可考虑：
- 封装为命令行工具 (CLI)
- 或开发 FastAPI 服务端
- pyseekdb持久化存储 (文件系统/NFS)
- 监控和日志记录
- 备份：定期备份 pyseekdb 数据目录
```

---

## 10. 开发路线图

### Phase 1: 核心功能开发 (Week 1-2)
- [x] 环境搭建
- [x] PageIndex集成
- [x] pyseekdb本地存储集成
- [x] 基础检索API
- [ ] 评测和优化

### Phase 2: 算法优化 (Week 3)
- [ ] 混合检索算法实现
- [ ] 结果融合策略优化
- [ ] 性能基准测试

### Phase 3: 评测与文章 (Week 4)
- [ ] 准备评测数据集
- [ ] 全面对比实验
- [ ] 撰写技术文章
- [ ] 开源代码发布

---

## 11. 风险与挑战

### 11.1 技术风险
- **风险**：PageIndex生成的树结构质量不稳定
- **缓解**：增加树结构质量验证，人工review

### 11.2 性能风险
- **风险**：混合检索延迟过高
- **缓解**：并行化、pyseekdb缓存、索引优化

### 11.3 数据管理风险
- **风险**：pyseekdb数据损坏或丢失
- **缓解**：定期备份数据目录、版本控制重要数据

---

## 附录

### A. 参考资料
- PageIndex论文: https://vectify.ai/blog/pageindex-intro
- seekdb文档: https://www.oceanbase.ai/docs
- Dify文档: https://docs.dify.ai

### B. 示例代码仓库
- GitHub: https://github.com/yourusername/pageindex-seekdb-rag

### C. 联系方式
- Email: your.email@example.com
- Issue Tracker: GitHub Issues
