"""
pyseekdb存储管理模块
使用pyseekdb本地持久化存储，无需部署数据库服务器
"""

import pyseekdb
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
from pydantic import BaseModel
import numpy as np
from pathlib import Path


class NodeRecord(BaseModel):
    """树节点记录"""
    node_id: str
    parent_id: Optional[str]
    document_id: str
    title: str
    summary: str
    level: int
    start_page: int
    end_page: int
    child_count: int
    metadata: Dict[str, Any] = {}


class ChunkRecord(BaseModel):
    """内容块记录"""
    chunk_id: str
    node_id: str
    document_id: str
    content: str
    page_num: int
    chunk_index: int
    word_count: int
    metadata: Dict[str, Any] = {}


class SearchResult(BaseModel):
    """检索结果"""
    chunk_id: str
    content: str
    score: float
    node_id: str
    node_path: List[str]
    page_num: int
    metadata: Dict[str, Any] = {}


class SeekDBManager:
    """pyseekdb本地数据库管理器"""

    def __init__(
        self,
        persist_directory: str = "./data/pyseekdb",
        database: str = "rag_system"
    ):
        """
        初始化pyseekdb管理器（嵌入式模式）

        Args:
            persist_directory: 本地数据存储目录
            database: 数据库名称
        """
        # 创建数据目录
        Path(persist_directory).mkdir(parents=True, exist_ok=True)

        # 使用嵌入式客户端
        self.client = pyseekdb.Client(
            path=persist_directory,
            database=database
        )

        self.nodes_collection = "tree_nodes"
        self.chunks_collection = "content_chunks"

        logger.info(f"Initialized pyseekdb at {persist_directory} (database: {database})")
    
    def initialize_collections(self, embedding_dims: int = 1536):
        """
        初始化Collections
        
        Args:
            embedding_dims: 向量维度
        """
        # 创建树节点Collection
        try:
            self.client.create_collection(
                name=self.nodes_collection,
                embedding_model_dims=embedding_dims,
                description="Document tree nodes with summary embeddings"
            )
            logger.info(f"Created collection: {self.nodes_collection}")
        except Exception as e:
            logger.warning(f"Collection {self.nodes_collection} may already exist: {e}")
        
        # 创建内容块Collection
        try:
            self.client.create_collection(
                name=self.chunks_collection,
                embedding_model_dims=embedding_dims,
                description="Document content chunks with embeddings"
            )
            logger.info(f"Created collection: {self.chunks_collection}")
        except Exception as e:
            logger.warning(f"Collection {self.chunks_collection} may already exist: {e}")
    
    def insert_nodes(
        self,
        nodes: List[NodeRecord],
        embeddings: List[List[float]]
    ) -> int:
        """
        批量插入树节点
        
        Args:
            nodes: 节点记录列表
            embeddings: 对应的向量列表
        
        Returns:
            插入的节点数量
        """
        if len(nodes) != len(embeddings):
            raise ValueError("nodes and embeddings must have the same length")
        
        collection = self.client.get_collection(self.nodes_collection)
        
        documents = []
        for node, embedding in zip(nodes, embeddings):
            doc = {
                "id": node.node_id,
                "document": node.summary,
                "embedding": embedding,
                "metadata": {
                    "parent_id": node.parent_id,
                    "document_id": node.document_id,
                    "title": node.title,
                    "level": node.level,
                    "start_page": node.start_page,
                    "end_page": node.end_page,
                    "child_count": node.child_count,
                    **node.metadata
                }
            }
            documents.append(doc)
        
        # 批量插入
        collection.add(documents=documents)
        logger.info(f"Inserted {len(nodes)} nodes into {self.nodes_collection}")
        
        return len(nodes)
    
    def insert_chunks(
        self,
        chunks: List[ChunkRecord],
        embeddings: List[List[float]]
    ) -> int:
        """
        批量插入内容块
        
        Args:
            chunks: 内容块列表
            embeddings: 对应的向量列表
        
        Returns:
            插入的块数量
        """
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        
        collection = self.client.get_collection(self.chunks_collection)
        
        documents = []
        for chunk, embedding in zip(chunks, embeddings):
            doc = {
                "id": chunk.chunk_id,
                "document": chunk.content,
                "embedding": embedding,
                "metadata": {
                    "node_id": chunk.node_id,
                    "document_id": chunk.document_id,
                    "page_num": chunk.page_num,
                    "chunk_index": chunk.chunk_index,
                    "word_count": chunk.word_count,
                    **chunk.metadata
                }
            }
            documents.append(doc)
        
        # 批量插入
        collection.add(documents=documents)
        logger.info(f"Inserted {len(chunks)} chunks into {self.chunks_collection}")
        
        return len(chunks)
    
    def search_nodes(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[NodeRecord, float]]:
        """
        向量搜索树节点
        
        Args:
            query_embedding: 查询向量
            top_k: 返回结果数量
            filter_dict: 过滤条件
        
        Returns:
            (节点, 分数)的列表
        """
        collection = self.client.get_collection(self.nodes_collection)
        
        # 执行向量检索
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_dict
        )
        
        # 解析结果
        node_results = []
        if results and results['ids']:
            for i, node_id in enumerate(results['ids'][0]):
                metadata = results['metadatas'][0][i]
                distance = results['distances'][0][i]
                
                # 转换距离为相似度分数 (cosine similarity)
                similarity = 1 - distance
                
                node = NodeRecord(
                    node_id=node_id,
                    parent_id=metadata.get('parent_id'),
                    document_id=metadata['document_id'],
                    title=metadata['title'],
                    summary=results['documents'][0][i],
                    level=metadata['level'],
                    start_page=metadata['start_page'],
                    end_page=metadata['end_page'],
                    child_count=metadata['child_count'],
                    metadata={k: v for k, v in metadata.items() 
                             if k not in ['parent_id', 'document_id', 'title', 'level',
                                         'start_page', 'end_page', 'child_count']}
                )
                
                node_results.append((node, similarity))
        
        return node_results
    
    def search_chunks(
        self,
        query_embedding: List[float],
        top_k: int = 20,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[ChunkRecord, float]]:
        """
        向量搜索内容块
        
        Args:
            query_embedding: 查询向量
            top_k: 返回结果数量
            filter_dict: 过滤条件
        
        Returns:
            (内容块, 分数)的列表
        """
        collection = self.client.get_collection(self.chunks_collection)
        
        # 执行向量检索
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_dict
        )
        
        # 解析结果
        chunk_results = []
        if results and results['ids']:
            for i, chunk_id in enumerate(results['ids'][0]):
                metadata = results['metadatas'][0][i]
                distance = results['distances'][0][i]
                
                # 转换距离为相似度分数
                similarity = 1 - distance
                
                chunk = ChunkRecord(
                    chunk_id=chunk_id,
                    node_id=metadata['node_id'],
                    document_id=metadata['document_id'],
                    content=results['documents'][0][i],
                    page_num=metadata['page_num'],
                    chunk_index=metadata['chunk_index'],
                    word_count=metadata['word_count'],
                    metadata={k: v for k, v in metadata.items()
                             if k not in ['node_id', 'document_id', 'page_num',
                                         'chunk_index', 'word_count']}
                )
                
                chunk_results.append((chunk, similarity))
        
        return chunk_results
    
    def get_chunks_by_node(
        self,
        node_id: str,
        document_id: Optional[str] = None
    ) -> List[ChunkRecord]:
        """
        获取指定节点的所有内容块
        
        Args:
            node_id: 节点ID
            document_id: 文档ID (可选)
        
        Returns:
            内容块列表
        """
        filter_dict = {"node_id": node_id}
        if document_id:
            filter_dict["document_id"] = document_id
        
        collection = self.client.get_collection(self.chunks_collection)
        
        # 使用get方法获取所有匹配的文档
        # 注意：pyseekdb可能没有直接的filter get，这里用query作为替代
        results = collection.get(where=filter_dict)
        
        chunks = []
        if results and results['ids']:
            for i, chunk_id in enumerate(results['ids']):
                metadata = results['metadatas'][i]
                chunk = ChunkRecord(
                    chunk_id=chunk_id,
                    node_id=metadata['node_id'],
                    document_id=metadata['document_id'],
                    content=results['documents'][i],
                    page_num=metadata['page_num'],
                    chunk_index=metadata['chunk_index'],
                    word_count=metadata['word_count'],
                    metadata={k: v for k, v in metadata.items()
                             if k not in ['node_id', 'document_id', 'page_num',
                                         'chunk_index', 'word_count']}
                )
                chunks.append(chunk)
        
        return sorted(chunks, key=lambda x: x.chunk_index)
    
    def delete_document(self, document_id: str) -> Dict[str, int]:
        """
        删除指定文档的所有数据
        
        Args:
            document_id: 文档ID
        
        Returns:
            删除统计信息
        """
        nodes_col = self.client.get_collection(self.nodes_collection)
        chunks_col = self.client.get_collection(self.chunks_collection)
        
        # 删除节点
        nodes_deleted = nodes_col.delete(where={"document_id": document_id})
        
        # 删除内容块
        chunks_deleted = chunks_col.delete(where={"document_id": document_id})
        
        logger.info(f"Deleted document {document_id}: "
                   f"{nodes_deleted} nodes, {chunks_deleted} chunks")
        
        return {
            "nodes_deleted": nodes_deleted or 0,
            "chunks_deleted": chunks_deleted or 0
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            nodes_col = self.client.get_collection(self.nodes_collection)
            chunks_col = self.client.get_collection(self.chunks_collection)
            
            # 获取文档数量
            nodes_count = nodes_col.count()
            chunks_count = chunks_col.count()
            
            return {
                "total_nodes": nodes_count,
                "total_chunks": chunks_count,
                "collections": [self.nodes_collection, self.chunks_collection]
            }
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                "error": str(e)
            }


# 测试代码
if __name__ == "__main__":
    # 创建管理器实例
    manager = SeekDBManager()
    
    # 初始化Collections
    manager.initialize_collections()
    
    # 获取统计信息
    stats = manager.get_statistics()
    print("Database statistics:")
    print(f"  Total nodes: {stats.get('total_nodes', 'N/A')}")
    print(f"  Total chunks: {stats.get('total_chunks', 'N/A')}")
