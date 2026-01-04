"""
配置管理模块
使用Pydantic Settings进行类型安全的配置管理
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
from pathlib import Path
import os

# 确保加载项目根目录的 .env 文件
from dotenv import load_dotenv

# 获取项目根目录（config.py 的父目录的父目录）
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

# 强制加载 .env 文件（override=True 确保覆盖已有的环境变量）
load_dotenv(ENV_FILE, override=True)


class OpenAIConfig(BaseSettings):
    """OpenAI 兼容 API 配置（支持 OpenAI、Qwen 等）"""
    model_config = SettingsConfigDict(extra='ignore')

    # 优先使用自定义 API_KEY，如果没有则使用 OPENAI_API_KEY
    api_key: str = Field(default="")
    openai_api_key: str = Field(default="")

    # 自定义 base_url（用于 Qwen、Azure OpenAI 等）
    base_url: Optional[str] = Field(default=None)

    # 模型名称
    model_name: str = Field(default="gpt-4o-2024-11-20")
    openai_model: str = Field(default="gpt-4o-2024-11-20")

    openai_embedding_model: str = Field(default="text-embedding-3-small")

    def get_api_key(self) -> str:
        """获取实际使用的 API Key"""
        return self.api_key or self.openai_api_key

    def get_model(self) -> str:
        """获取实际使用的模型名称"""
        return self.model_name if self.model_name != "gpt-4o-2024-11-20" else self.openai_model


class SeekDBConfig(BaseSettings):
    """seekdb配置（支持Embedded和Server两种模式）"""
    model_config = SettingsConfigDict(extra='ignore')

    # 运行模式: "embedded" 或 "server"
    seekdb_mode: str = Field(default="server")

    # Embedded模式配置
    seekdb_persist_dir: str = Field(default="./data/pyseekdb")

    # Server模式配置
    seekdb_host: str = Field(default="127.0.0.1")
    seekdb_port: int = Field(default=2881)
    seekdb_user: str = Field(default="root")
    seekdb_password: str = Field(default="")

    # 通用配置
    seekdb_database: str = Field(default="rag_system")
    embedding_dims: int = Field(default=1536)


class PageIndexConfig(BaseSettings):
    """PageIndex配置"""
    model_config = SettingsConfigDict(extra='ignore')

    pageindex_model: str = Field(default="gpt-4o-2024-11-20")
    pageindex_toc_check_pages: int = Field(default=20)
    pageindex_max_pages_per_node: int = Field(default=10)
    pageindex_max_tokens_per_node: int = Field(default=20000)


class SearchConfig(BaseSettings):
    """检索配置"""
    model_config = SettingsConfigDict(extra='ignore')

    # 混合检索权重
    tree_search_weight: float = Field(default=0.4)
    vector_search_weight: float = Field(default=0.6)

    # 树搜索参数
    tree_max_depth: int = Field(default=3)
    tree_top_k_per_level: int = Field(default=5)
    tree_similarity_threshold: float = Field(default=0.6)

    # 向量检索参数
    vector_top_k: int = Field(default=20)
    chunk_size: int = Field(default=500)
    chunk_overlap: int = Field(default=50)


class CacheConfig(BaseSettings):
    """缓存配置（使用pyseekdb存储）"""
    model_config = SettingsConfigDict(extra='ignore')

    enable_cache: bool = Field(default=True)
    cache_ttl: int = Field(default=900)  # 15分钟
    cache_collection: str = Field(default="cache_data")


class Config(BaseSettings):
    """主配置类 - 聚合所有子配置"""
    model_config = SettingsConfigDict(extra='ignore')

    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    seekdb: SeekDBConfig = Field(default_factory=SeekDBConfig)
    pageindex: PageIndexConfig = Field(default_factory=PageIndexConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)


# 全局配置实例
config = Config()
