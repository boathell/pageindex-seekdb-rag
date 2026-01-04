"""
混合检索引擎
结合树结构检索和向量检索的核心模块
"""

from typing import List, Dict, Any, Tuple, Optional
from loguru import logger
from pydantic import BaseModel
import numpy as np
from collections import defaultdict

from .seekdb_manager import SeekDBManager, NodeRecord, ChunkRecord, SearchResult
from .embedding_manager import EmbeddingManager
from .cache_manager import CacheManager


class TreeSearchConfig(BaseModel):
    """树搜索配置"""
    max_depth: int = 3
    top_k_per_level: int = 5
    similarity_threshold: float = 0.6
    enable_pruning: bool = True


class VectorSearchConfig(BaseModel):
    """向量搜索配置"""
    top_k: int = 20
    enable_rerank: bool = False


class HybridSearchConfig(BaseModel):
    """混合检索配置"""
    tree_weight: float = 0.4
    vector_weight: float = 0.6
    tree_config: TreeSearchConfig = TreeSearchConfig()
    vector_config: VectorSearchConfig = VectorSearchConfig()


class HybridSearchEngine:
    """混合检索引擎"""
    
    def __init__(
        self,
        seekdb_manager: SeekDBManager,
        embedding_manager: EmbeddingManager,
        cache_manager: Optional[CacheManager] = None,
        config: Optional[HybridSearchConfig] = None
    ):
        """
        初始化混合检索引擎

        Args:
            seekdb_manager: seekdb管理器
            embedding_manager: embedding管理器
            cache_manager: 缓存管理器（可选）
            config: 检索配置
        """
        self.db = seekdb_manager
        self.embed = embedding_manager
        self.cache = cache_manager
        self.config = config or HybridSearchConfig()

        cache_status = "enabled" if cache_manager and cache_manager.enable_cache else "disabled"
        logger.info(f"Initialized HybridSearchEngine (cache: {cache_status})")
    
    def tree_search(
        self,
        query_embedding: List[float],
        document_id: Optional[str] = None,
        config: Optional[TreeSearchConfig] = None
    ) -> List[Tuple[NodeRecord, float]]:
        """
        基于推理的树结构检索
        
        Args:
            query_embedding: 查询向量
            document_id: 文档ID筛选
            config: 树搜索配置
        
        Returns:
            (节点, 分数)的列表
        """
        cfg = config or self.config.tree_config
        
        # 1. 搜索根节点
        filter_dict = {"level": 0}
        if document_id:
            filter_dict["document_id"] = document_id
        
        root_results = self.db.search_nodes(
            query_embedding=query_embedding,
            top_k=cfg.top_k_per_level,
            filter_dict=filter_dict
        )
        
        logger.debug(f"Found {len(root_results)} root nodes")
        
        # 2. BFS遍历
        relevant_nodes = []
        queue = [(node, score, 1) for node, score in root_results]  # (node, score, depth)
        
        while queue:
            current_node, current_score, depth = queue.pop(0)
            
            # 相似度阈值剪枝
            if cfg.enable_pruning and current_score < cfg.similarity_threshold:
                logger.debug(f"Pruned node {current_node.node_id} "
                           f"(score: {current_score:.3f})")
                continue
            
            # 添加到结果
            relevant_nodes.append((current_node, current_score))
            logger.debug(f"Added node {current_node.node_id} "
                       f"(level: {depth}, score: {current_score:.3f})")
            
            # 深度限制
            if depth >= cfg.max_depth:
                continue
            
            # 3. 搜索子节点
            if current_node.child_count > 0:
                child_filter = {"parent_id": current_node.node_id}
                if document_id:
                    child_filter["document_id"] = document_id
                
                children = self.db.search_nodes(
                    query_embedding=query_embedding,
                    top_k=cfg.top_k_per_level,
                    filter_dict=child_filter
                )
                
                # 加入队列
                for child_node, child_score in children:
                    # 层级加权：越深层相关性越高
                    depth_bonus = depth * 0.1
                    adjusted_score = child_score + depth_bonus
                    queue.append((child_node, adjusted_score, depth + 1))
        
        logger.info(f"Tree search found {len(relevant_nodes)} relevant nodes")
        return relevant_nodes
    
    def vector_search(
        self,
        query_embedding: List[float],
        document_id: Optional[str] = None,
        node_ids: Optional[List[str]] = None,
        config: Optional[VectorSearchConfig] = None
    ) -> List[Tuple[ChunkRecord, float]]:
        """
        向量语义检索
        
        Args:
            query_embedding: 查询向量
            document_id: 文档ID筛选
            node_ids: 节点ID筛选（限定在特定节点内检索）
            config: 向量搜索配置
        
        Returns:
            (内容块, 分数)的列表
        """
        cfg = config or self.config.vector_config
        
        # 构建过滤条件
        filter_dict = {}
        if document_id:
            filter_dict["document_id"] = document_id
        
        # 如果指定了节点，只在这些节点内搜索
        if node_ids:
            # 注意：pyseekdb可能不支持IN查询，需要多次查询
            all_results = []
            for node_id in node_ids:
                node_filter = {**filter_dict, "node_id": node_id}
                results = self.db.search_chunks(
                    query_embedding=query_embedding,
                    top_k=cfg.top_k // len(node_ids) if len(node_ids) > 0 else cfg.top_k,
                    filter_dict=node_filter
                )
                all_results.extend(results)
            
            # 按分数排序
            all_results.sort(key=lambda x: x[1], reverse=True)
            results = all_results[:cfg.top_k]
        else:
            # 全局搜索
            results = self.db.search_chunks(
                query_embedding=query_embedding,
                top_k=cfg.top_k,
                filter_dict=filter_dict if filter_dict else None
            )
        
        logger.info(f"Vector search found {len(results)} chunks")
        return results
    
    def hybrid_search(
        self,
        query: str,
        document_id: Optional[str] = None,
        strategy: str = "hybrid",  # "tree_only", "vector_only", "hybrid"
        config: Optional[HybridSearchConfig] = None
    ) -> List[SearchResult]:
        """
        混合检索：结合树结构和向量检索

        Args:
            query: 查询文本
            document_id: 文档ID
            strategy: 检索策略
            config: 混合检索配置

        Returns:
            SearchResult列表
        """
        cfg = config or self.config

        # 0. 尝试从缓存获取结果
        if self.cache:
            cached_results = self.cache.get_query_cache(
                query=query,
                document_id=document_id,
                strategy=strategy
            )
            if cached_results is not None:
                # 将字典列表转换回SearchResult对象
                return [SearchResult(**result) for result in cached_results]

        # 1. 生成查询向量
        query_embedding = self.embed.embed(query)
        logger.info(f"Query: {query[:100]}...")

        # 2. 根据策略执行检索
        if strategy == "tree_only":
            # 仅树检索
            tree_results = self.tree_search(query_embedding, document_id, cfg.tree_config)
            vector_results = []
            
        elif strategy == "vector_only":
            # 仅向量检索
            tree_results = []
            vector_results = self.vector_search(query_embedding, document_id, None, cfg.vector_config)
            
        else:  # hybrid
            # 并行检索
            logger.info("Executing hybrid search...")
            
            # 树检索
            tree_results = self.tree_search(query_embedding, document_id, cfg.tree_config)
            
            # 向量检索（可选：限定在树检索的节点内）
            tree_node_ids = [node.node_id for node, _ in tree_results]
            vector_results = self.vector_search(
                query_embedding,
                document_id,
                node_ids=None,  # 或 tree_node_ids 来限定范围
                config=cfg.vector_config
            )
        
        # 3. 融合结果
        merged_results = self._merge_results(
            tree_results=tree_results,
            vector_results=vector_results,
            alpha=cfg.tree_weight,
            beta=cfg.vector_weight,
            document_id=document_id
        )

        # 4. 保存到缓存
        if self.cache:
            # 将SearchResult对象转换为字典以便序列化
            results_dict = [result.dict() for result in merged_results]
            self.cache.set_query_cache(
                query=query,
                results=results_dict,
                document_id=document_id,
                strategy=strategy
            )

        return merged_results
    
    def _merge_results(
        self,
        tree_results: List[Tuple[NodeRecord, float]],
        vector_results: List[Tuple[ChunkRecord, float]],
        alpha: float,
        beta: float,
        document_id: Optional[str] = None
    ) -> List[SearchResult]:
        """
        融合树检索和向量检索的结果
        
        Args:
            tree_results: 树检索结果
            vector_results: 向量检索结果
            alpha: 树检索权重
            beta: 向量检索权重
            document_id: 文档ID
        
        Returns:
            融合后的SearchResult列表
        """
        # 使用字典存储融合结果
        merged = {}
        
        # 1. 分数归一化
        tree_scores = [score for _, score in tree_results]
        vector_scores = [score for _, score in vector_results]
        
        tree_scores_norm = self._normalize_scores(tree_scores)
        vector_scores_norm = self._normalize_scores(vector_scores)
        
        # 2. 处理树检索结果
        for i, (node, _) in enumerate(tree_results):
            # 获取该节点下的所有chunks
            chunks = self.db.get_chunks_by_node(node.node_id, document_id)
            
            for chunk in chunks:
                chunk_id = chunk.chunk_id
                
                # 树检索得分（层级加权）
                tree_score = tree_scores_norm[i] if i < len(tree_scores_norm) else 0
                level_bonus = (node.level + 1) * 0.1  # 层级越深，bonus越高
                final_tree_score = alpha * (tree_score + level_bonus)
                
                if chunk_id not in merged:
                    merged[chunk_id] = {
                        "chunk": chunk,
                        "node": node,
                        "score": final_tree_score,
                        "from_tree": True,
                        "from_vector": False,
                        "tree_score": tree_score,
                        "vector_score": 0.0
                    }
                else:
                    merged[chunk_id]["score"] += final_tree_score
                    merged[chunk_id]["from_tree"] = True
                    merged[chunk_id]["tree_score"] = tree_score
        
        # 3. 处理向量检索结果
        for i, (chunk, _) in enumerate(vector_results):
            chunk_id = chunk.chunk_id
            
            # 向量检索得分
            vector_score = vector_scores_norm[i] if i < len(vector_scores_norm) else 0
            final_vector_score = beta * vector_score
            
            if chunk_id not in merged:
                # 需要获取节点信息
                node = self._get_node_info(chunk.node_id, document_id)
                
                merged[chunk_id] = {
                    "chunk": chunk,
                    "node": node,
                    "score": final_vector_score,
                    "from_tree": False,
                    "from_vector": True,
                    "tree_score": 0.0,
                    "vector_score": vector_score
                }
            else:
                merged[chunk_id]["score"] += final_vector_score
                merged[chunk_id]["from_vector"] = True
                merged[chunk_id]["vector_score"] = vector_score
        
        # 4. 转换为SearchResult并排序
        search_results = []
        for item in merged.values():
            chunk = item["chunk"]
            node = item["node"]
            
            # 构建节点路径
            node_path = self._build_node_path(node)
            
            result = SearchResult(
                chunk_id=chunk.chunk_id,
                content=chunk.content,
                score=item["score"],
                node_id=chunk.node_id,
                node_path=node_path,
                page_num=chunk.page_num,
                metadata={
                    "from_tree": item["from_tree"],
                    "from_vector": item["from_vector"],
                    "tree_score": item["tree_score"],
                    "vector_score": item["vector_score"],
                    "node_title": node.title if node else "",
                    "node_level": node.level if node else 0,
                    **chunk.metadata
                }
            )
            search_results.append(result)
        
        # 按分数排序
        search_results.sort(key=lambda x: x.score, reverse=True)
        
        logger.info(f"Merged {len(search_results)} unique results")
        return search_results[:20]  # 返回top 20
    
    def _normalize_scores(self, scores: List[float]) -> List[float]:
        """Min-Max归一化分数"""
        if not scores:
            return []
        
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score == min_score:
            return [1.0] * len(scores)
        
        return [(s - min_score) / (max_score - min_score) for s in scores]
    
    def _get_node_info(self, node_id: str, document_id: Optional[str]) -> Optional[NodeRecord]:
        """获取节点信息"""
        filter_dict = {"node_id": node_id}
        if document_id:
            filter_dict["document_id"] = document_id
        
        # 使用零向量查询（只需要获取元数据）
        dummy_embedding = [0.0] * 1536
        results = self.db.search_nodes(
            query_embedding=dummy_embedding,
            top_k=1,
            filter_dict=filter_dict
        )
        
        if results:
            return results[0][0]
        return None
    
    def _build_node_path(self, node: Optional[NodeRecord]) -> List[str]:
        """构建节点路径"""
        if not node:
            return []
        
        path = [node.title]
        current_parent_id = node.parent_id
        
        # 向上追溯父节点
        while current_parent_id:
            parent_node = self._get_node_info(current_parent_id, node.document_id)
            if parent_node:
                path.insert(0, parent_node.title)
                current_parent_id = parent_node.parent_id
            else:
                break
        
        return path


# 测试代码
if __name__ == "__main__":
    from .config import config
    
    # 初始化组件
    db_manager = SeekDBManager(
        mode=config.seekdb.seekdb_mode,
        persist_directory=config.seekdb.seekdb_persist_dir,
        host=config.seekdb.seekdb_host,
        port=config.seekdb.seekdb_port,
        user=config.seekdb.seekdb_user,
        password=config.seekdb.seekdb_password,
        database=config.seekdb.seekdb_database
    )

    embed_manager = EmbeddingManager(
        api_key=config.openai.get_api_key(),
        model=config.openai.openai_embedding_model,
        base_url=config.openai.base_url
    )
    
    # 创建检索引擎
    search_engine = HybridSearchEngine(
        seekdb_manager=db_manager,
        embedding_manager=embed_manager
    )
    
    # 测试检索
    query = "What is the main topic of this document?"
    results = search_engine.hybrid_search(query, strategy="hybrid")
    
    print(f"\nFound {len(results)} results:")
    for i, result in enumerate(results[:5], 1):
        print(f"\n{i}. Score: {result.score:.4f}")
        print(f"   Path: {' > '.join(result.node_path)}")
        print(f"   Content: {result.content[:200]}...")
