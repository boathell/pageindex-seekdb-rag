"""
Embedding管理模块
负责文本向量化
"""

from typing import List, Union
from openai import OpenAI
from loguru import logger
import numpy as np
from functools import lru_cache
import hashlib


class EmbeddingManager:
    """Embedding管理器"""
    
    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        base_url: str = None,
        batch_size: int = 100,
        cache_size: int = 1000
    ):
        """
        初始化Embedding管理器

        Args:
            api_key: OpenAI 兼容 API 密钥
            model: Embedding模型名称
            base_url: 自定义 API base URL（可选，用于兼容其他服务）
            batch_size: 批处理大小
            cache_size: 缓存大小
        """
        # 创建客户端，支持自定义 base_url
        if base_url:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
            logger.info(f"Using custom base_url: {base_url}")
        else:
            self.client = OpenAI(api_key=api_key)

        self.model = model
        self.batch_size = batch_size

        # 设置缓存
        self._embed_single_cached = lru_cache(maxsize=cache_size)(
            self._embed_single
        )

        logger.info(f"Initialized EmbeddingManager with model: {model}")
    
    def _embed_single(self, text: str) -> List[float]:
        """
        对单个文本进行向量化（内部方法，支持缓存）
        
        Args:
            text: 输入文本
        
        Returns:
            向量
        """
        response = self.client.embeddings.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding
    
    def embed(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        对文本进行向量化
        
        Args:
            text: 单个文本或文本列表
        
        Returns:
            向量或向量列表
        """
        # 单个文本
        if isinstance(text, str):
            # 使用缓存版本
            return self._embed_single_cached(text)
        
        # 文本列表
        if not text:
            return []
        
        # 批量处理
        all_embeddings = []
        for i in range(0, len(text), self.batch_size):
            batch = text[i:i + self.batch_size]
            
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch
                )
                
                # 提取向量
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                
                logger.debug(f"Embedded batch {i//self.batch_size + 1}: "
                           f"{len(batch)} texts")
                
            except Exception as e:
                logger.error(f"Embedding batch failed: {e}")
                # 逐个处理失败的批次
                for text_item in batch:
                    try:
                        emb = self._embed_single_cached(text_item)
                        all_embeddings.append(emb)
                    except Exception as e2:
                        logger.error(f"Failed to embed single text: {e2}")
                        # 使用零向量作为fallback
                        all_embeddings.append([0.0] * 1536)
        
        return all_embeddings
    
    def cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float]
    ) -> float:
        """
        计算余弦相似度
        
        Args:
            vec1: 向量1
            vec2: 向量2
        
        Returns:
            相似度分数 [0, 1]
        """
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def get_cache_info(self) -> dict:
        """获取缓存信息"""
        return {
            "cache_info": self._embed_single_cached.cache_info()._asdict()
        }
    
    def clear_cache(self):
        """清空缓存"""
        self._embed_single_cached.cache_clear()
        logger.info("Embedding cache cleared")


# 测试代码
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    manager = EmbeddingManager(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="text-embedding-3-small"
    )
    
    # 测试单个文本
    text1 = "What is the capital of France?"
    emb1 = manager.embed(text1)
    print(f"Single embedding shape: {len(emb1)}")
    
    # 测试批量
    texts = [
        "Machine learning is a subset of AI",
        "Deep learning uses neural networks",
        "Python is a popular programming language"
    ]
    embs = manager.embed(texts)
    print(f"Batch embeddings: {len(embs)} x {len(embs[0])}")
    
    # 测试相似度
    sim = manager.cosine_similarity(embs[0], embs[1])
    print(f"Similarity between first two: {sim:.4f}")
    
    # 缓存信息
    print(f"Cache info: {manager.get_cache_info()}")
