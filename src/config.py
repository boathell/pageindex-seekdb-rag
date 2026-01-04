"""
配置管理模块
使用Pydantic Settings进行类型安全的配置管理
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class OpenAIConfig(BaseSettings):
    """OpenAI配置"""
    api_key: str = Field(..., env="OPENAI_API_KEY")
    model: str = Field(default="gpt-4o-2024-11-20", env="OPENAI_MODEL")
    embedding_model: str = Field(
        default="text-embedding-3-small",
        env="OPENAI_EMBEDDING_MODEL"
    )
    
    class Config:
        env_file = ".env"


class PySeekDBConfig(BaseSettings):
    """pyseekdb本地存储配置"""
    persist_directory: str = Field(
        default="./data/pyseekdb",
        env="PYSEEKDB_PERSIST_DIR"
    )
    embedding_dims: int = Field(default=1536, env="EMBEDDING_DIMS")

    class Config:
        env_file = ".env"


class PageIndexConfig(BaseSettings):
    """PageIndex配置"""
    model: str = Field(default="gpt-4o-2024-11-20", env="PAGEINDEX_MODEL")
    toc_check_pages: int = Field(default=20, env="PAGEINDEX_TOC_CHECK_PAGES")
    max_pages_per_node: int = Field(default=10, env="PAGEINDEX_MAX_PAGES_PER_NODE")
    max_tokens_per_node: int = Field(default=20000, env="PAGEINDEX_MAX_TOKENS_PER_NODE")
    
    class Config:
        env_file = ".env"


class SearchConfig(BaseSettings):
    """检索配置"""
    # 混合检索权重
    tree_weight: float = Field(default=0.4, env="TREE_SEARCH_WEIGHT")
    vector_weight: float = Field(default=0.6, env="VECTOR_SEARCH_WEIGHT")
    
    # 树搜索参数
    tree_max_depth: int = Field(default=3, env="TREE_MAX_DEPTH")
    tree_top_k: int = Field(default=5, env="TREE_TOP_K_PER_LEVEL")
    tree_threshold: float = Field(default=0.6, env="TREE_SIMILARITY_THRESHOLD")
    
    # 向量检索参数
    vector_top_k: int = Field(default=20, env="VECTOR_TOP_K")
    chunk_size: int = Field(default=500, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, env="CHUNK_OVERLAP")
    
    class Config:
        env_file = ".env"


class CacheConfig(BaseSettings):
    """缓存配置（使用pyseekdb存储）"""
    enable_cache: bool = Field(default=True, env="ENABLE_CACHE")
    cache_ttl: int = Field(default=900, env="CACHE_TTL")  # 15分钟
    cache_collection: str = Field(default="cache_data", env="CACHE_COLLECTION")

    class Config:
        env_file = ".env"


class Config(BaseSettings):
    """主配置类 - 聚合所有子配置"""
    openai: OpenAIConfig = OpenAIConfig()
    pyseekdb: PySeekDBConfig = PySeekDBConfig()
    pageindex: PageIndexConfig = PageIndexConfig()
    search: SearchConfig = SearchConfig()
    cache: CacheConfig = CacheConfig()

    class Config:
        env_file = ".env"


# 全局配置实例
config = Config()
