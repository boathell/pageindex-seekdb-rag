# pyseekdb 缓存方案设计

## 概述

为了提升系统性能并降低 OpenAI API 调用成本，我们使用 **pyseekdb 本身** 来存储缓存数据，保持架构的简洁性和一致性。

## 缓存架构

```
┌─────────────────────────────────────┐
│        应用层                        │
│  - 文档索引                          │
│  - 混合检索                          │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│     缓存管理层 (cache_manager.py)   │
│  - 查询结果缓存                      │
│  - 树结构缓存                        │
│  - Embedding缓存 (LRU内存)          │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│         pyseekdb本地存储             │
│  Collections:                        │
│  - tree_nodes (树节点)               │
│  - content_chunks (内容块)           │
│  - cache_data (缓存数据) ← 新增      │
└─────────────────────────────────────┘
```

## 缓存类型

### 1. Embedding 缓存（内存LRU）

**策略**：使用 Python 内置 `functools.lru_cache`

**原因**：
- Embedding 向量较小，适合内存缓存
- LRU 自动淘汰，无需手动管理
- 访问速度极快

**实现**：

```python
from functools import lru_cache

class EmbeddingManager:
    @lru_cache(maxsize=1000)
    def embed(self, text: str) -> List[float]:
        """缓存Embedding结果"""
        return self._call_openai_api(text)
```

### 2. 查询结果缓存（pyseekdb）

**策略**：使用 pyseekdb 的 `cache_data` collection

**数据结构**：

```python
{
    "id": "query_hash_12345",
    "document": json.dumps({
        "query": "原始查询文本",
        "results": [...],  # 检索结果
        "timestamp": 1704268800,
        "ttl": 900  # 15分钟
    }),
    "embedding": [0.0] * 1536,  # 占位向量
    "metadata": {
        "cache_type": "query_result",
        "document_id": "doc_001",
        "strategy": "hybrid",
        "expired_at": 1704269700
    }
}
```

**优势**：
- 持久化存储，重启后仍有效
- 支持 TTL 过期清理
- 与主数据共享存储

### 3. 树结构缓存（pyseekdb）

**策略**：将解析后的文档树存储到 `cache_data` collection

**数据结构**：

```python
{
    "id": f"tree_{document_id}",
    "document": json.dumps({
        "tree": {...},  # PageIndex生成的树结构
        "timestamp": 1704268800
    }),
    "embedding": [0.0] * 1536,  # 占位向量
    "metadata": {
        "cache_type": "document_tree",
        "document_id": "doc_001",
        "version": "1.0"
    }
}
```

**优势**：
- 避免重复调用 PageIndex 解析
- PDF 文档树不常变化，可长期缓存
- 节省 OpenAI API 调用

## 实现代码框架

### cache_manager.py

```python
"""
缓存管理模块
使用pyseekdb存储缓存数据
"""

import json
import time
import hashlib
from typing import Optional, Dict, Any, List
from loguru import logger
import pyseekdb


class CacheManager:
    """缓存管理器（基于pyseekdb）"""

    def __init__(self, client: pyseekdb.PersistentClient, ttl: int = 900):
        """
        Args:
            client: pyseekdb客户端
            ttl: 缓存过期时间（秒）
        """
        self.client = client
        self.ttl = ttl
        self.cache_collection = "cache_data"
        self._init_cache_collection()

    def _init_cache_collection(self):
        """初始化缓存collection"""
        try:
            self.client.create_collection(
                name=self.cache_collection,
                embedding_model_dims=1536
            )
            logger.info(f"Created cache collection: {self.cache_collection}")
        except Exception as e:
            logger.debug(f"Cache collection already exists: {e}")

    def _get_query_hash(self, query: str, **kwargs) -> str:
        """生成查询哈希ID"""
        key = f"{query}_{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(key.encode()).hexdigest()

    def get_query_cache(
        self,
        query: str,
        document_id: Optional[str] = None,
        strategy: str = "hybrid"
    ) -> Optional[List[Dict]]:
        """
        获取查询结果缓存

        Returns:
            缓存的检索结果，未命中返回None
        """
        cache_id = self._get_query_hash(
            query,
            document_id=document_id,
            strategy=strategy
        )

        collection = self.client.get_collection(self.cache_collection)

        try:
            result = collection.get(ids=[cache_id])

            if not result or not result['ids']:
                return None

            # 解析缓存数据
            cache_data = json.loads(result['documents'][0])

            # 检查是否过期
            if time.time() > cache_data.get('expired_at', 0):
                logger.debug(f"Cache expired for query: {query[:50]}")
                return None

            logger.info(f"Cache hit for query: {query[:50]}")
            return cache_data['results']

        except Exception as e:
            logger.warning(f"Cache get failed: {e}")
            return None

    def set_query_cache(
        self,
        query: str,
        results: List[Dict],
        document_id: Optional[str] = None,
        strategy: str = "hybrid"
    ):
        """保存查询结果到缓存"""
        cache_id = self._get_query_hash(
            query,
            document_id=document_id,
            strategy=strategy
        )

        collection = self.client.get_collection(self.cache_collection)

        cache_data = {
            "query": query,
            "results": results,
            "timestamp": int(time.time()),
            "expired_at": int(time.time()) + self.ttl
        }

        try:
            collection.add(
                ids=[cache_id],
                documents=[json.dumps(cache_data)],
                embeddings=[[0.0] * 1536],  # 占位向量
                metadatas=[{
                    "cache_type": "query_result",
                    "document_id": document_id or "",
                    "strategy": strategy
                }]
            )
            logger.info(f"Cached query result: {query[:50]}")
        except Exception as e:
            logger.warning(f"Cache set failed: {e}")

    def get_tree_cache(self, document_id: str) -> Optional[Dict]:
        """获取文档树缓存"""
        cache_id = f"tree_{document_id}"
        collection = self.client.get_collection(self.cache_collection)

        try:
            result = collection.get(ids=[cache_id])

            if not result or not result['ids']:
                return None

            cache_data = json.loads(result['documents'][0])
            logger.info(f"Tree cache hit for document: {document_id}")
            return cache_data['tree']

        except Exception as e:
            logger.warning(f"Tree cache get failed: {e}")
            return None

    def set_tree_cache(self, document_id: str, tree: Dict):
        """保存文档树到缓存"""
        cache_id = f"tree_{document_id}"
        collection = self.client.get_collection(self.cache_collection)

        cache_data = {
            "tree": tree,
            "timestamp": int(time.time())
        }

        try:
            collection.add(
                ids=[cache_id],
                documents=[json.dumps(cache_data)],
                embeddings=[[0.0] * 1536],
                metadatas=[{
                    "cache_type": "document_tree",
                    "document_id": document_id
                }]
            )
            logger.info(f"Cached document tree: {document_id}")
        except Exception as e:
            logger.warning(f"Tree cache set failed: {e}")

    def clear_expired_cache(self):
        """清理过期缓存"""
        collection = self.client.get_collection(self.cache_collection)
        current_time = int(time.time())

        try:
            # 获取所有查询结果类型的缓存
            results = collection.get(
                where={"cache_type": "query_result"}
            )

            expired_ids = []
            for i, doc_str in enumerate(results['documents']):
                cache_data = json.loads(doc_str)
                if current_time > cache_data.get('expired_at', 0):
                    expired_ids.append(results['ids'][i])

            if expired_ids:
                collection.delete(ids=expired_ids)
                logger.info(f"Cleared {len(expired_ids)} expired cache entries")

        except Exception as e:
            logger.warning(f"Cache cleanup failed: {e}")


# 使用示例
if __name__ == "__main__":
    import pyseekdb

    client = pyseekdb.PersistentClient(path="./data/pyseekdb")
    cache_manager = CacheManager(client, ttl=900)

    # 测试查询缓存
    results = cache_manager.get_query_cache("test query")
    if results is None:
        # 执行实际检索
        results = [{"content": "...", "score": 0.9}]
        cache_manager.set_query_cache("test query", results)

    # 清理过期缓存
    cache_manager.clear_expired_cache()
```

## 集成到现有系统

### 修改 hybrid_search.py

```python
class HybridSearchEngine:
    def __init__(
        self,
        seekdb_manager: SeekDBManager,
        embedding_manager: EmbeddingManager,
        cache_manager: Optional[CacheManager] = None,
        config: Optional[HybridSearchConfig] = None
    ):
        self.db = seekdb_manager
        self.embed = embedding_manager
        self.cache = cache_manager  # 新增
        self.config = config or HybridSearchConfig()

    def hybrid_search(
        self,
        query: str,
        document_id: Optional[str] = None,
        strategy: str = "hybrid"
    ) -> List[SearchResult]:
        # 1. 尝试从缓存获取
        if self.cache:
            cached_results = self.cache.get_query_cache(
                query, document_id, strategy
            )
            if cached_results:
                return cached_results

        # 2. 执行实际检索
        results = self._do_search(query, document_id, strategy)

        # 3. 保存到缓存
        if self.cache:
            self.cache.set_query_cache(
                query, results, document_id, strategy
            )

        return results
```

## 性能优化建议

1. **定期清理**：
   - 设置定时任务清理过期缓存
   - 或在每次检索时异步清理

2. **缓存预热**：
   - 对常见查询预先生成缓存
   - 在索引完成后立即缓存树结构

3. **内存vs磁盘**：
   - 热数据用内存LRU（Embedding）
   - 冷数据用pyseekdb（查询结果、树结构）

4. **缓存命中率监控**：
   - 记录缓存命中/未命中次数
   - 分析优化缓存策略

## 总结

**优势**：
- ✅ 统一存储：所有数据都在 pyseekdb
- ✅ 零额外部署：无需 Redis 等外部服务
- ✅ 持久化：重启后缓存仍有效
- ✅ 简单清晰：符合项目"简单直接"的理念

**下一步**：
- 实现 `cache_manager.py` 模块
- 集成到混合检索引擎
- 添加单元测试
- 性能测试和优化
