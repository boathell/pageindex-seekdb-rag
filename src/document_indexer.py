"""
文档索引器
整合PageIndex解析和seekdb存储
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
from loguru import logger
import PyPDF2
from tqdm import tqdm

from .pageindex_parser import PageIndexParser, DocumentTree, TreeNode
from .seekdb_manager import SeekDBManager, NodeRecord, ChunkRecord
from .embedding_manager import EmbeddingManager


class DocumentIndexer:
    """文档索引器"""

    def __init__(
        self,
        openai_api_key: str,
        seekdb_mode: str = "server",
        # Embedded模式参数
        persist_directory: str = "./data/pyseekdb",
        # Server模式参数
        seekdb_host: str = "127.0.0.1",
        seekdb_port: int = 2881,
        seekdb_user: str = "root",
        seekdb_password: str = "",
        seekdb_database: str = "rag_system",
        # 其他参数
        pageindex_config: Optional[Dict[str, Any]] = None,
        embedding_model: str = "text-embedding-3-small",
        embedding_base_url: Optional[str] = None,
        embedding_dims: int = 1536,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        """
        初始化文档索引器

        Args:
            openai_api_key: OpenAI API密钥
            seekdb_mode: seekdb运行模式 ("embedded" 或 "server")
            persist_directory: 本地存储目录（Embedded模式）
            seekdb_host: seekdb服务器地址（Server模式）
            seekdb_port: seekdb服务器端口（Server模式）
            seekdb_user: 用户名（Server模式）
            seekdb_password: 密码（Server模式）
            seekdb_database: 数据库名称
            pageindex_config: PageIndex配置字典
            embedding_model: Embedding模型名称
            embedding_base_url: Embedding API端点
            embedding_dims: 向量维度
            chunk_size: 文本块大小
            chunk_overlap: 文本块重叠大小
        """
        # 初始化组件
        self.parser = PageIndexParser(**(pageindex_config or {}))

        self.db = SeekDBManager(
            mode=seekdb_mode,
            persist_directory=persist_directory,
            host=seekdb_host,
            port=seekdb_port,
            user=seekdb_user,
            password=seekdb_password,
            database=seekdb_database
        )

        self.embed = EmbeddingManager(
            api_key=openai_api_key,
            model=embedding_model,
            base_url=embedding_base_url
        )

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # 初始化数据库collections
        self.db.initialize_collections(embedding_dims=embedding_dims)

        logger.info(f"DocumentIndexer initialized (seekdb mode: {seekdb_mode})")
    
    def index_document(
        self,
        pdf_path: str,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        索引PDF文档
        
        Args:
            pdf_path: PDF文件路径
            document_id: 文档ID
            metadata: 额外元数据
        
        Returns:
            索引统计信息
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        document_id = document_id or pdf_path.stem
        logger.info(f"Indexing document: {document_id}")
        
        # 1. 使用PageIndex解析文档
        logger.info("Step 1: Parsing with PageIndex...")
        tree = self.parser.parse_pdf(
            pdf_path=str(pdf_path),
            document_id=document_id
        )
        
        # 2. 提取PDF文本内容
        logger.info("Step 2: Extracting text from PDF...")
        page_texts = self._extract_pdf_text(pdf_path)
        
        # 3. 处理树节点
        logger.info("Step 3: Processing tree nodes...")
        all_nodes = self.parser.flatten_tree(tree)
        node_records = self._create_node_records(all_nodes, tree, metadata)
        
        # 4. 生成节点摘要的embedding
        logger.info("Step 4: Generating node embeddings...")
        node_summaries = [node.summary for node in node_records]
        node_embeddings = self.embed.embed(node_summaries)
        
        # 5. 存储节点
        logger.info("Step 5: Storing nodes...")
        self.db.insert_nodes(node_records, node_embeddings)
        
        # 6. 分块处理内容
        logger.info("Step 6: Chunking content...")
        chunk_records = self._create_chunks(all_nodes, page_texts, document_id)
        
        # 7. 生成内容embedding
        logger.info("Step 7: Generating chunk embeddings...")
        chunk_texts = [chunk.content for chunk in chunk_records]
        chunk_embeddings = []
        
        # 分批处理embedding（避免超限）
        batch_size = 100
        for i in tqdm(range(0, len(chunk_texts), batch_size), desc="Embedding chunks"):
            batch = chunk_texts[i:i+batch_size]
            batch_embs = self.embed.embed(batch)
            chunk_embeddings.extend(batch_embs)
        
        # 8. 存储内容块
        logger.info("Step 8: Storing chunks...")
        self.db.insert_chunks(chunk_records, chunk_embeddings)
        
        # 9. 返回统计信息
        stats = {
            "document_id": document_id,
            "total_pages": tree.total_pages,
            "total_nodes": len(node_records),
            "total_chunks": len(chunk_records),
            "tree_depth": max(node.level for node in node_records),
            "avg_chunks_per_node": len(chunk_records) / len(node_records) if node_records else 0
        }
        
        logger.info(f"Indexing complete: {stats}")
        return stats
    
    def _extract_pdf_text(self, pdf_path: Path) -> Dict[int, str]:
        """
        提取PDF每页的文本
        
        Args:
            pdf_path: PDF文件路径
        
        Returns:
            页码 -> 文本内容的字典
        """
        page_texts = {}
        
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                text = page.extract_text()
                page_texts[page_num + 1] = text  # 1-indexed
        
        logger.debug(f"Extracted text from {len(page_texts)} pages")
        return page_texts
    
    def _create_node_records(
        self,
        nodes: List[TreeNode],
        tree: DocumentTree,
        metadata: Optional[Dict[str, Any]]
    ) -> List[NodeRecord]:
        """
        创建节点记录
        
        Args:
            nodes: 树节点列表
            tree: 文档树
            metadata: 额外元数据
        
        Returns:
            节点记录列表
        """
        records = []
        
        for node in nodes:
            record = NodeRecord(
                node_id=node.node_id,
                parent_id=node.parent_id,
                document_id=tree.document_id,
                title=node.title,
                summary=node.summary,
                level=node.level,
                start_page=node.start_index,
                end_page=node.end_index,
                child_count=len(node.nodes),
                metadata=metadata or {}
            )
            records.append(record)
        
        return records
    
    def _create_chunks(
        self,
        nodes: List[TreeNode],
        page_texts: Dict[int, str],
        document_id: str
    ) -> List[ChunkRecord]:
        """
        创建内容块
        
        Args:
            nodes: 树节点列表
            page_texts: 页面文本字典
            document_id: 文档ID
        
        Returns:
            内容块记录列表
        """
        all_chunks = []
        
        for node in nodes:
            # 提取该节点对应的页面文本
            node_text = ""
            for page_num in range(node.start_index, node.end_index + 1):
                if page_num in page_texts:
                    node_text += page_texts[page_num] + "\n"
            
            if not node_text.strip():
                continue
            
            # 分块
            chunks = self._chunk_text(
                text=node_text,
                chunk_size=self.chunk_size,
                overlap=self.chunk_overlap
            )
            
            # 创建chunk records
            for i, chunk_text in enumerate(chunks):
                # 估算chunk所在页码
                chunk_page = node.start_index + int(i * len(chunks) / (node.end_index - node.start_index + 1))
                
                chunk_record = ChunkRecord(
                    chunk_id=f"{node.node_id}_chunk_{i}",
                    node_id=node.node_id,
                    document_id=document_id,
                    content=chunk_text,
                    page_num=chunk_page,
                    chunk_index=i,
                    word_count=len(chunk_text.split()),
                    metadata={
                        "node_title": node.title,
                        "node_level": node.level
                    }
                )
                all_chunks.append(chunk_record)
        
        return all_chunks
    
    def _chunk_text(
        self,
        text: str,
        chunk_size: int,
        overlap: int
    ) -> List[str]:
        """
        文本分块
        
        Args:
            text: 输入文本
            chunk_size: 块大小（字符数）
            overlap: 重叠大小
        
        Returns:
            文本块列表
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # 尝试在句号、换行等位置断开
            if end < len(text):
                # 查找最近的句子边界
                boundary_chars = ['. ', '.\n', '! ', '?\n']
                best_boundary = -1
                
                for char in boundary_chars:
                    pos = text.rfind(char, start, end)
                    if pos > best_boundary:
                        best_boundary = pos
                
                if best_boundary > start:
                    end = best_boundary + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # 移动起始位置（考虑重叠）
            start = end - overlap if end < len(text) else len(text)
        
        return chunks
    
    def delete_document(self, document_id: str) -> Dict[str, int]:
        """
        删除文档索引
        
        Args:
            document_id: 文档ID
        
        Returns:
            删除统计
        """
        logger.info(f"Deleting document: {document_id}")
        stats = self.db.delete_document(document_id)
        logger.info(f"Deleted: {stats}")
        return stats


# 测试代码
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    import sys
    
    load_dotenv()
    
    if len(sys.argv) < 2:
        print("Usage: python document_indexer.py <pdf_path>")
        sys.exit(1)
    
    # 创建索引器
    indexer = DocumentIndexer(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        seekdb_config={
            "host": os.getenv("SEEKDB_HOST", "127.0.0.1"),
            "port": int(os.getenv("SEEKDB_PORT", 2881)),
            "database": os.getenv("SEEKDB_DATABASE", "rag_system")
        }
    )
    
    # 索引文档
    pdf_path = sys.argv[1]
    stats = indexer.index_document(pdf_path)
    
    print("\n索引完成！")
    print(f"文档ID: {stats['document_id']}")
    print(f"总页数: {stats['total_pages']}")
    print(f"节点数: {stats['total_nodes']}")
    print(f"内容块: {stats['total_chunks']}")
    print(f"树深度: {stats['tree_depth']}")
