"""
seekdb存储管理模块
支持两种模式：
1. Embedded模式：本地文件存储，无需部署服务器
2. Server模式：连接Docker部署的seekdb服务器
"""

import pyseekdb
from pyseekdb import HNSWConfiguration
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
    """seekdb数据库管理器（支持Embedded和Server两种模式）"""

    def __init__(
        self,
        mode: str = "embedded",
        # Embedded模式参数
        persist_directory: str = "./data/pyseekdb",
        # Server模式参数
        host: str = "127.0.0.1",
        port: int = 2881,
        user: str = "root",
        password: str = "",
        # 通用参数
        database: str = "rag_system"
    ):
        """
        初始化seekdb管理器

        Args:
            mode: 运行模式 ("embedded" 或 "server")
            persist_directory: 本地数据存储目录（Embedded模式）
            host: seekdb服务器地址（Server模式）
            port: seekdb服务器端口（Server模式）
            user: 用户名（Server模式）
            password: 密码（Server模式）
            database: 数据库名称
        """
        self.mode = mode.lower()

        if self.mode == "embedded":
            # 创建数据目录
            Path(persist_directory).mkdir(parents=True, exist_ok=True)

            # 使用嵌入式客户端
            self.client = pyseekdb.Client(
                path=persist_directory,
                database=database
            )
            logger.info(f"Initialized seekdb in EMBEDDED mode at {persist_directory} (database: {database})")

        elif self.mode == "server":
            # 连接到seekdb服务器
            self.client = pyseekdb.Client(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password
            )
            logger.info(f"Connected to seekdb SERVER at {host}:{port} (database: {database}, user: {user})")

        else:
            raise ValueError(f"Invalid mode: {mode}. Must be 'embedded' or 'server'")

        self.nodes_collection = "tree_nodes"
        self.chunks_collection = "content_chunks"
    
    def initialize_collections(self, embedding_dims: int = 1536):
        """
        初始化Collections

        Args:
            embedding_dims: 向量维度
        """
        # 创建HNSW配置
        config = HNSWConfiguration(dimension=embedding_dims, distance="cosine")

        # 创建树节点Collection (不使用pyseekdb的embedding function，我们自己管理embeddings)
        try:
            self.client.create_collection(
                name=self.nodes_collection,
                configuration=config,
                embedding_function=None,  # 明确禁用pyseekdb的embedding function
                description="Document tree nodes with summary embeddings"
            )
            logger.info(f"Created collection: {self.nodes_collection} with {embedding_dims} dimensions")
        except Exception as e:
            logger.warning(f"Collection {self.nodes_collection} may already exist: {e}")

        # 创建内容块Collection (不使用pyseekdb的embedding function)
        try:
            self.client.create_collection(
                name=self.chunks_collection,
                configuration=config,
                embedding_function=None,  # 明确禁用pyseekdb的embedding function
                description="Document content chunks with embeddings"
            )
            logger.info(f"Created collection: {self.chunks_collection} with {embedding_dims} dimensions")
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

        # 准备数据（分离 documents, embeddings, metadatas）
        ids = [node.node_id for node in nodes]
        documents = [node.summary for node in nodes]
        metadatas = [
            {
                "parent_id": node.parent_id,
                "document_id": node.document_id,
                "title": node.title,
                "level": node.level,
                "start_page": node.start_page,
                "end_page": node.end_page,
                "child_count": node.child_count,
                **node.metadata
            }
            for node in nodes
        ]

        # 调试信息
        logger.info(f"Preparing to insert {len(ids)} nodes")
        logger.debug(f"IDs: {ids}")
        logger.debug(f"Documents count: {len(documents)}")
        logger.debug(f"Embeddings count: {len(embeddings)}")
        logger.debug(f"Metadatas count: {len(metadatas)}")

        # 批量插入（ids 是第一个位置参数）
        collection.add(
            ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )
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
        if len(chunks) == 0:
            logger.warning("No chunks to insert")
            return 0

        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")

        collection = self.client.get_collection(self.chunks_collection)

        # 准备数据（分离 documents, embeddings, metadatas）
        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = [
            {
                "node_id": chunk.node_id,
                "document_id": chunk.document_id,
                "page_num": chunk.page_num,
                "chunk_index": chunk.chunk_index,
                "word_count": chunk.word_count,
                **chunk.metadata
            }
            for chunk in chunks
        ]

        # 批量插入（ids 是第一个位置参数）
        collection.add(
            ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )
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

    def get_stats(self) -> Dict[str, Any]:
        """get_statistics 的别名，用于 API 兼容性"""
        return self.get_statistics()

    def list_documents(self) -> List[Dict[str, Any]]:
        """
        列出所有已索引的文档

        Returns:
            文档列表，每个文档包含 document_id 和统计信息
        """
        try:
            nodes_col = self.client.get_collection(self.nodes_collection)

            # 获取所有根节点（level=0）来识别文档
            result = nodes_col.get(
                where={"level": 0},
                include=["metadatas"]
            )

            # 提取唯一的 document_id
            documents = {}
            if result and result.get('metadatas'):
                for metadata in result['metadatas']:
                    doc_id = metadata.get('document_id')
                    if doc_id and doc_id not in documents:
                        # 统计该文档的节点和块数
                        nodes_count = nodes_col.count(where={"document_id": doc_id})
                        chunks_col = self.client.get_collection(self.chunks_collection)
                        chunks_count = chunks_col.count(where={"document_id": doc_id})

                        documents[doc_id] = {
                            "document_id": doc_id,
                            "total_nodes": nodes_count,
                            "total_chunks": chunks_count,
                            "title": metadata.get('title', 'Unknown')
                        }

            return list(documents.values())

        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return []


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
