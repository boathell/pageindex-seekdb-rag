"""
缓存管理模块
使用pyseekdb存储缓存数据，提升检索性能并降低API调用成本
"""

import json
import time
import hashlib
from typing import Optional, Dict, Any, List
from loguru import logger
import pyseekdb


class CacheManager:
    """缓存管理器（基于pyseekdb）"""

    def __init__(
        self,
        client: pyseekdb.Client,
        ttl: int = 900,
        enable_cache: bool = True
    ):
        """
        初始化缓存管理器

        Args:
            client: pyseekdb客户端实例（Client）
            ttl: 缓存过期时间（秒），默认15分钟
            enable_cache: 是否启用缓存
        """
        self.client = client
        self.ttl = ttl
        self.enable_cache = enable_cache
        self.cache_collection = "cache_data"

        if self.enable_cache:
            self._init_cache_collection()
            logger.info(f"CacheManager initialized (TTL: {ttl}s)")
        else:
            logger.info("CacheManager disabled")

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
        """
        生成查询哈希ID

        Args:
            query: 查询文本
            **kwargs: 其他参数（document_id, strategy等）

        Returns:
            MD5哈希字符串
        """
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

        Args:
            query: 查询文本
            document_id: 文档ID
            strategy: 检索策略

        Returns:
            缓存的检索结果，未命中返回None
        """
        if not self.enable_cache:
            return None

        cache_id = self._get_query_hash(
            query,
            document_id=document_id,
            strategy=strategy
        )

        collection = self.client.get_collection(self.cache_collection)

        try:
            result = collection.get(ids=[cache_id])

            if not result or not result['ids']:
                logger.debug(f"Cache miss for query: {query[:50]}...")
                return None

            # 解析缓存数据
            cache_data = json.loads(result['documents'][0])

            # 检查是否过期
            if time.time() > cache_data.get('expired_at', 0):
                logger.debug(f"Cache expired for query: {query[:50]}...")
                # 异步删除过期缓存
                try:
                    collection.delete(ids=[cache_id])
                except Exception:
                    pass
                return None

            logger.info(f"✓ Cache hit for query: {query[:50]}...")
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
        """
        保存查询结果到缓存

        Args:
            query: 查询文本
            results: 检索结果列表
            document_id: 文档ID
            strategy: 检索策略
        """
        if not self.enable_cache:
            return

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
            # 先尝试删除旧缓存（如果存在）
            try:
                collection.delete(ids=[cache_id])
            except Exception:
                pass

            # 添加新缓存
            collection.add(
                ids=[cache_id],
                documents=[json.dumps(cache_data)],
                embeddings=[[0.0] * 1536],  # 占位向量
                metadatas=[{
                    "cache_type": "query_result",
                    "document_id": document_id or "",
                    "strategy": strategy,
                    "expired_at": cache_data["expired_at"]
                }]
            )
            logger.info(f"✓ Cached query result: {query[:50]}...")
        except Exception as e:
            logger.warning(f"Cache set failed: {e}")

    def get_tree_cache(self, document_id: str) -> Optional[Dict]:
        """
        获取文档树缓存

        Args:
            document_id: 文档ID

        Returns:
            缓存的文档树，未命中返回None
        """
        if not self.enable_cache:
            return None

        cache_id = f"tree_{document_id}"
        collection = self.client.get_collection(self.cache_collection)

        try:
            result = collection.get(ids=[cache_id])

            if not result or not result['ids']:
                logger.debug(f"Tree cache miss for document: {document_id}")
                return None

            cache_data = json.loads(result['documents'][0])
            logger.info(f"✓ Tree cache hit for document: {document_id}")
            return cache_data['tree']

        except Exception as e:
            logger.warning(f"Tree cache get failed: {e}")
            return None

    def set_tree_cache(self, document_id: str, tree: Dict):
        """
        保存文档树到缓存

        Args:
            document_id: 文档ID
            tree: PageIndex生成的文档树结构
        """
        if not self.enable_cache:
            return

        cache_id = f"tree_{document_id}"
        collection = self.client.get_collection(self.cache_collection)

        cache_data = {
            "tree": tree,
            "timestamp": int(time.time())
        }

        try:
            # 先尝试删除旧缓存
            try:
                collection.delete(ids=[cache_id])
            except Exception:
                pass

            # 添加新缓存
            collection.add(
                ids=[cache_id],
                documents=[json.dumps(cache_data)],
                embeddings=[[0.0] * 1536],
                metadatas=[{
                    "cache_type": "document_tree",
                    "document_id": document_id,
                    "timestamp": cache_data["timestamp"]
                }]
            )
            logger.info(f"✓ Cached document tree: {document_id}")
        except Exception as e:
            logger.warning(f"Tree cache set failed: {e}")

    def clear_expired_cache(self) -> int:
        """
        清理过期缓存

        Returns:
            清理的缓存条目数量
        """
        if not self.enable_cache:
            return 0

        collection = self.client.get_collection(self.cache_collection)
        current_time = int(time.time())
        cleared_count = 0

        try:
            # 获取所有查询结果类型的缓存
            results = collection.get(
                where={"cache_type": "query_result"}
            )

            if not results or not results['ids']:
                return 0

            expired_ids = []
            for i, doc_str in enumerate(results['documents']):
                try:
                    cache_data = json.loads(doc_str)
                    if current_time > cache_data.get('expired_at', 0):
                        expired_ids.append(results['ids'][i])
                except Exception as e:
                    logger.warning(f"Failed to parse cache data: {e}")
                    expired_ids.append(results['ids'][i])

            if expired_ids:
                collection.delete(ids=expired_ids)
                cleared_count = len(expired_ids)
                logger.info(f"✓ Cleared {cleared_count} expired cache entries")

        except Exception as e:
            logger.warning(f"Cache cleanup failed: {e}")

        return cleared_count

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            缓存统计字典
        """
        if not self.enable_cache:
            return {"enabled": False}

        try:
            collection = self.client.get_collection(self.cache_collection)

            # 获取所有缓存
            all_cache = collection.get()

            if not all_cache or not all_cache['ids']:
                return {
                    "enabled": True,
                    "total_entries": 0,
                    "query_results": 0,
                    "document_trees": 0
                }

            query_count = 0
            tree_count = 0

            for metadata in all_cache['metadatas']:
                cache_type = metadata.get('cache_type', '')
                if cache_type == 'query_result':
                    query_count += 1
                elif cache_type == 'document_tree':
                    tree_count += 1

            return {
                "enabled": True,
                "total_entries": len(all_cache['ids']),
                "query_results": query_count,
                "document_trees": tree_count,
                "ttl_seconds": self.ttl
            }

        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return {"enabled": True, "error": str(e)}

    def clear_all_cache(self) -> int:
        """
        清空所有缓存

        Returns:
            清理的缓存条目数量
        """
        if not self.enable_cache:
            return 0

        try:
            collection = self.client.get_collection(self.cache_collection)
            all_cache = collection.get()

            if not all_cache or not all_cache['ids']:
                return 0

            count = len(all_cache['ids'])
            collection.delete(ids=all_cache['ids'])
            logger.info(f"✓ Cleared all {count} cache entries")
            return count

        except Exception as e:
            logger.warning(f"Failed to clear all cache: {e}")
            return 0


# 测试代码
if __name__ == "__main__":
    import pyseekdb

    # 创建测试客户端（嵌入式模式）
    client = pyseekdb.Client(
        path="./data/pyseekdb_test",
        database="test"
    )
    cache_manager = CacheManager(client, ttl=900)

    # 测试查询缓存
    print("\n=== 测试查询缓存 ===")
    test_query = "什么是PageIndex？"
    test_results = [
        {"content": "PageIndex是一个推理式RAG框架", "score": 0.95},
        {"content": "PageIndex使用树结构组织文档", "score": 0.88}
    ]

    # 第一次查询 - 缓存未命中
    cached = cache_manager.get_query_cache(test_query, document_id="test_doc")
    print(f"第一次查询缓存结果: {cached}")

    # 设置缓存
    cache_manager.set_query_cache(test_query, test_results, document_id="test_doc")

    # 第二次查询 - 缓存命中
    cached = cache_manager.get_query_cache(test_query, document_id="test_doc")
    print(f"第二次查询缓存结果: {cached is not None}")

    # 测试树缓存
    print("\n=== 测试树缓存 ===")
    test_tree = {"root": {"title": "测试文档", "children": []}}

    cache_manager.set_tree_cache("test_doc", test_tree)
    cached_tree = cache_manager.get_tree_cache("test_doc")
    print(f"树缓存结果: {cached_tree is not None}")

    # 获取统计信息
    print("\n=== 缓存统计 ===")
    stats = cache_manager.get_cache_stats()
    print(f"缓存统计: {stats}")

    # 清理测试
    print("\n=== 清理测试 ===")
    cleared = cache_manager.clear_all_cache()
    print(f"清理了 {cleared} 条缓存")
