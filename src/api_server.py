"""
FastAPI REST API 服务
提供文档索引和检索的 HTTP 接口
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from pathlib import Path
import tempfile
import shutil
from loguru import logger
import traceback

from .config import config
from .document_indexer import DocumentIndexer
from .hybrid_search import HybridSearchEngine, HybridSearchConfig, TreeSearchConfig, VectorSearchConfig
from .seekdb_manager import SeekDBManager
from .embedding_manager import EmbeddingManager
from .cache_manager import CacheManager

# ============================================================================
# API Models (Request/Response)
# ============================================================================

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str = "0.2.0"
    seekdb_mode: str
    cache_enabled: bool


class IndexRequest(BaseModel):
    """文档索引请求"""
    document_id: str = Field(..., description="文档唯一标识")
    pdf_path: Optional[str] = Field(None, description="PDF文件路径（与file上传二选一）")

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "sample_001",
                "pdf_path": "data/sample.pdf"
            }
        }


class IndexResponse(BaseModel):
    """文档索引响应"""
    success: bool
    document_id: str
    total_nodes: int
    total_chunks: int
    total_pages: int
    message: str


class SearchRequest(BaseModel):
    """检索请求"""
    query: str = Field(..., description="检索查询")
    document_id: Optional[str] = Field(None, description="文档ID过滤")
    strategy: Literal["tree_only", "vector_only", "hybrid"] = Field(
        "hybrid", description="检索策略"
    )
    top_k: int = Field(5, ge=1, le=100, description="返回结果数量")

    # 高级配置（可选）
    tree_weight: Optional[float] = Field(None, ge=0, le=1)
    vector_weight: Optional[float] = Field(None, ge=0, le=1)
    tree_max_depth: Optional[int] = Field(None, ge=1, le=10)

    class Config:
        json_schema_extra = {
            "example": {
                "query": "文档的主要主题是什么？",
                "document_id": "sample_001",
                "strategy": "hybrid",
                "top_k": 5
            }
        }


class SearchResultItem(BaseModel):
    """单个检索结果"""
    score: float = Field(..., description="相关性分数")
    content: str = Field(..., description="内容文本")
    node_path: List[str] = Field(..., description="章节路径")
    page_num: int = Field(..., description="页码")
    chunk_id: Optional[str] = Field(None, description="内容块ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class SearchResponse(BaseModel):
    """检索响应"""
    success: bool
    query: str
    strategy: str
    total_results: int
    results: List[SearchResultItem]


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    success: bool
    total_documents: int
    documents: List[Dict[str, Any]]


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error: str
    detail: Optional[str] = None


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="PageIndex + seekdb 混合 RAG API",
    description="结合结构化推理检索和向量语义检索的 RAG 系统",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Global Instances (延迟初始化)
# ============================================================================

db_manager: Optional[SeekDBManager] = None
embed_manager: Optional[EmbeddingManager] = None
cache_manager: Optional[CacheManager] = None
search_engine: Optional[HybridSearchEngine] = None
document_indexer: Optional[DocumentIndexer] = None


def initialize_services():
    """初始化所有服务"""
    global db_manager, embed_manager, cache_manager, search_engine, document_indexer

    try:
        logger.info("Initializing API services...")

        # 1. 初始化 seekdb 管理器
        db_manager = SeekDBManager(
            mode=config.seekdb.seekdb_mode,
            persist_directory=config.seekdb.seekdb_persist_dir,
            host=config.seekdb.seekdb_host,
            port=config.seekdb.seekdb_port,
            user=config.seekdb.seekdb_user,
            password=config.seekdb.seekdb_password,
            database=config.seekdb.seekdb_database
        )

        # 2. 初始化 embedding 管理器
        embed_manager = EmbeddingManager(
            api_key=config.openai.get_api_key(),
            model=config.openai.openai_embedding_model,
            base_url=config.openai.base_url
        )

        # 3. 初始化缓存管理器
        if config.cache.enable_cache:
            cache_manager = CacheManager(
                seekdb_manager=db_manager,
                embedding_manager=embed_manager,
                enable_cache=True,
                ttl=config.cache.cache_ttl,
                collection_name=config.cache.cache_collection
            )
            logger.info("Cache enabled")
        else:
            cache_manager = None
            logger.info("Cache disabled")

        # 4. 初始化检索引擎
        search_engine = HybridSearchEngine(
            seekdb_manager=db_manager,
            embedding_manager=embed_manager,
            cache_manager=cache_manager
        )

        # 5. 初始化文档索引器
        document_indexer = DocumentIndexer(
            openai_api_key=config.openai.get_api_key(),
            seekdb_mode=config.seekdb.seekdb_mode,
            embedding_dims=config.seekdb.embedding_dims,
            persist_directory=config.seekdb.seekdb_persist_dir,
            seekdb_host=config.seekdb.seekdb_host,
            seekdb_port=config.seekdb.seekdb_port,
            seekdb_user=config.seekdb.seekdb_user,
            seekdb_password=config.seekdb.seekdb_password,
            seekdb_database=config.seekdb.seekdb_database,
            base_url=config.openai.base_url,
            model_name=config.openai.model_name
        )

        logger.success("All services initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        logger.error(traceback.format_exc())
        raise


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化服务"""
    initialize_services()


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    logger.info("Shutting down API services...")
    # 这里可以添加资源清理逻辑


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """根路径"""
    return {
        "name": "PageIndex + seekdb 混合 RAG API",
        "version": "0.2.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """健康检查"""
    try:
        return HealthResponse(
            status="healthy",
            seekdb_mode=config.seekdb.seekdb_mode,
            cache_enabled=config.cache.enable_cache
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@app.post("/index", response_model=IndexResponse, tags=["Indexing"])
async def index_document(request: IndexRequest, background_tasks: BackgroundTasks):
    """
    索引文档

    将 PDF 文档解析并索引到 seekdb
    """
    try:
        if not request.pdf_path:
            raise HTTPException(status_code=400, detail="pdf_path is required")

        pdf_path = Path(request.pdf_path)
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail=f"PDF file not found: {pdf_path}")

        logger.info(f"Indexing document: {request.document_id}")

        # 执行索引
        result = document_indexer.index_document(
            pdf_path=str(pdf_path),
            document_id=request.document_id
        )

        return IndexResponse(
            success=True,
            document_id=request.document_id,
            total_nodes=result['total_nodes'],
            total_chunks=result['total_chunks'],
            total_pages=result['total_pages'],
            message=f"Document indexed successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error indexing document: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/index/upload", response_model=IndexResponse, tags=["Indexing"])
async def index_upload(
    document_id: str,
    file: UploadFile = File(..., description="PDF 文件")
):
    """
    上传并索引文档

    通过文件上传方式索引 PDF 文档
    """
    try:
        # 检查文件类型
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        # 保存上传文件到临时目录
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_path = Path(tmp_file.name)
            shutil.copyfileobj(file.file, tmp_file)

        try:
            logger.info(f"Indexing uploaded document: {document_id}")

            # 执行索引
            result = document_indexer.index_document(
                pdf_path=str(tmp_path),
                document_id=document_id
            )

            return IndexResponse(
                success=True,
                document_id=document_id,
                total_nodes=result['total_nodes'],
                total_chunks=result['total_chunks'],
                total_pages=result['total_pages'],
                message=f"Document indexed successfully"
            )

        finally:
            # 清理临时文件
            tmp_path.unlink(missing_ok=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error indexing uploaded document: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", response_model=SearchResponse, tags=["Search"])
async def search(request: SearchRequest):
    """
    混合检索

    支持三种检索策略：tree_only（树检索）、vector_only（向量检索）、hybrid（混合检索）
    """
    try:
        logger.info(f"Search query: {request.query} (strategy: {request.strategy})")

        # 构建检索配置
        hybrid_config = None
        if request.tree_weight is not None or request.vector_weight is not None:
            tree_weight = request.tree_weight if request.tree_weight is not None else 0.4
            vector_weight = request.vector_weight if request.vector_weight is not None else 0.6

            tree_config = TreeSearchConfig()
            if request.tree_max_depth is not None:
                tree_config.max_depth = request.tree_max_depth

            hybrid_config = HybridSearchConfig(
                tree_weight=tree_weight,
                vector_weight=vector_weight,
                tree_config=tree_config
            )

        # 执行检索
        results = search_engine.hybrid_search(
            query=request.query,
            document_id=request.document_id,
            strategy=request.strategy,
            top_k=request.top_k,
            config=hybrid_config
        )

        # 转换结果
        result_items = [
            SearchResultItem(
                score=result.score,
                content=result.content,
                node_path=result.node_path,
                page_num=result.page_num,
                chunk_id=result.chunk_id,
                metadata=result.metadata
            )
            for result in results
        ]

        return SearchResponse(
            success=True,
            query=request.query,
            strategy=request.strategy,
            total_results=len(result_items),
            results=result_items
        )

    except Exception as e:
        logger.error(f"Error during search: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents", response_model=DocumentListResponse, tags=["Documents"])
async def list_documents():
    """
    列出所有已索引的文档
    """
    try:
        # 从 seekdb 获取所有文档
        documents = db_manager.list_documents()

        return DocumentListResponse(
            success=True,
            total_documents=len(documents),
            documents=documents
        )

    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{document_id}", tags=["Documents"])
async def delete_document(document_id: str):
    """
    删除指定文档的所有数据
    """
    try:
        logger.info(f"Deleting document: {document_id}")

        stats = db_manager.delete_document(document_id)

        return {
            "success": True,
            "document_id": document_id,
            "nodes_deleted": stats.get('nodes_deleted', 0),
            "chunks_deleted": stats.get('chunks_deleted', 0),
            "message": f"Document deleted successfully"
        }

    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", tags=["System"])
async def get_stats():
    """
    获取系统统计信息
    """
    try:
        stats = db_manager.get_stats()

        return {
            "success": True,
            "stats": stats,
            "cache_enabled": config.cache.enable_cache,
            "seekdb_mode": config.seekdb.seekdb_mode
        }

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Main (用于开发测试)
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
