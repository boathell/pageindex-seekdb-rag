"""
混合检索 + 缓存 完整示例
演示如何使用缓存提升混合检索性能
"""

import sys
import os
import time
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
load_dotenv(project_root / ".env")

from src import (
    config,
    SeekDBManager,
    EmbeddingManager,
    CacheManager,
    HybridSearchEngine
)
from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stderr, level="INFO")


def demo_with_cache():
    """演示启用缓存的混合检索"""
    print("\n" + "="*70)
    print("混合检索 + 缓存演示（启用缓存）")
    print("="*70)

    # 1. 初始化组件
    print("\n[1] 初始化组件...")
    print("-" * 70)

    # pyseekdb客户端（嵌入式模式）
    import pyseekdb
    data_dir = project_root / config.pyseekdb.persist_directory
    data_dir.mkdir(parents=True, exist_ok=True)

    client = pyseekdb.Client(
        path=str(data_dir),
        database="rag_system"
    )

    # SeekDB管理器
    db_manager = SeekDBManager(
        persist_directory=str(data_dir)
    )

    # Embedding管理器
    embed_manager = EmbeddingManager(
        api_key=config.openai.api_key,
        model=config.openai.embedding_model
    )

    # 缓存管理器（启用）
    cache_manager = CacheManager(
        client=client,
        ttl=config.cache.cache_ttl,
        enable_cache=True
    )

    # 混合检索引擎
    search_engine = HybridSearchEngine(
        seekdb_manager=db_manager,
        embedding_manager=embed_manager,
        cache_manager=cache_manager  # 传入缓存管理器
    )

    print("✓ 所有组件初始化完成")

    # 2. 模拟检索（第一次 - 无缓存）
    print("\n[2] 第一次检索（无缓存）...")
    print("-" * 70)

    test_query = "PageIndex的核心优势是什么？"

    start_time = time.time()
    try:
        results = search_engine.hybrid_search(
            query=test_query,
            document_id="sample_doc",
            strategy="hybrid"
        )
        elapsed = time.time() - start_time

        print(f"✓ 检索完成")
        print(f"  查询: {test_query}")
        print(f"  耗时: {elapsed*1000:.2f}ms")
        print(f"  结果数: {len(results)}")

    except Exception as e:
        print(f"✗ 检索失败: {e}")
        print("  注意：这是预期的，因为数据库中可能还没有数据")

    # 3. 第二次相同检索（有缓存）
    print("\n[3] 第二次相同检索（应该命中缓存）...")
    print("-" * 70)

    start_time = time.time()
    try:
        results = search_engine.hybrid_search(
            query=test_query,
            document_id="sample_doc",
            strategy="hybrid"
        )
        elapsed = time.time() - start_time

        print(f"✓ 检索完成")
        print(f"  查询: {test_query}")
        print(f"  耗时: {elapsed*1000:.2f}ms  ← 应该明显更快！")
        print(f"  结果数: {len(results)}")

    except Exception as e:
        print(f"✗ 检索失败: {e}")

    # 4. 查看缓存统计
    print("\n[4] 缓存统计信息...")
    print("-" * 70)

    stats = cache_manager.get_cache_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # 5. 查看Embedding缓存
    print("\n[5] Embedding缓存信息...")
    print("-" * 70)

    embed_cache_info = embed_manager.get_cache_info()
    cache_info = embed_cache_info['cache_info']
    print(f"  命中次数: {cache_info['hits']}")
    print(f"  未命中次数: {cache_info['misses']}")
    print(f"  缓存大小: {cache_info['currsize']}/{cache_info['maxsize']}")
    hit_rate = cache_info['hits'] / (cache_info['hits'] + cache_info['misses']) * 100 if cache_info['hits'] + cache_info['misses'] > 0 else 0
    print(f"  命中率: {hit_rate:.1f}%")

    print("\n" + "="*70)
    print("演示完成！")
    print("="*70)


def demo_without_cache():
    """演示禁用缓存的混合检索（对比）"""
    print("\n" + "="*70)
    print("混合检索演示（禁用缓存 - 用于对比）")
    print("="*70)

    # 1. 初始化组件（不使用缓存）
    print("\n[1] 初始化组件（缓存已禁用）...")
    print("-" * 70)

    import pyseekdb
    data_dir = project_root / config.pyseekdb.persist_directory
    data_dir.mkdir(parents=True, exist_ok=True)

    # pyseekdb客户端（嵌入式模式） - 禁用缓存演示不需要
    # client = pyseekdb.Client(path=str(data_dir), database="rag_system")

    # SeekDB管理器
    db_manager = SeekDBManager(
        persist_directory=str(data_dir)
    )

    # Embedding管理器
    embed_manager = EmbeddingManager(
        api_key=config.openai.api_key,
        model=config.openai.embedding_model
    )

    # 混合检索引擎（不传入缓存管理器）
    search_engine = HybridSearchEngine(
        seekdb_manager=db_manager,
        embedding_manager=embed_manager,
        cache_manager=None  # 禁用缓存
    )

    print("✓ 组件初始化完成（无缓存）")

    # 2. 多次相同检索（观察时间）
    print("\n[2] 执行3次相同检索（观察时间变化）...")
    print("-" * 70)

    test_query = "混合RAG系统的技术架构是什么？"

    for i in range(3):
        start_time = time.time()
        try:
            results = search_engine.hybrid_search(
                query=test_query,
                document_id="sample_doc",
                strategy="hybrid"
            )
            elapsed = time.time() - start_time

            print(f"\n  第{i+1}次检索:")
            print(f"    耗时: {elapsed*1000:.2f}ms")
            print(f"    结果数: {len(results)}")

        except Exception as e:
            print(f"\n  第{i+1}次检索失败: {e}")

    print("\n注意：没有缓存时，每次检索耗时应该相近")

    print("\n" + "="*70)
    print("演示完成！")
    print("="*70)


def show_performance_comparison():
    """性能对比总结"""
    print("\n" + "="*70)
    print("性能对比总结")
    print("="*70)

    print("""
启用缓存的优势：

1. 查询结果缓存
   - 第一次查询：需要完整检索（树搜索 + 向量搜索）
   - 后续相同查询：直接返回缓存结果
   - 性能提升：10-100x（取决于检索复杂度）

2. Embedding缓存（LRU）
   - 相同文本无需重复调用OpenAI API
   - 节省API成本
   - 降低网络延迟

3. 树结构缓存
   - PageIndex解析结果缓存
   - 避免重复解析PDF
   - 节省计算资源

适用场景：

✅ 高频重复查询
✅ 交互式问答系统
✅ 批量评测实验
✅ 开发调试阶段

注意事项：

- 缓存占用磁盘空间（pyseekdb存储）
- 缓存可能过期（默认15分钟）
- 文档更新后需清理缓存
    """)

    print("="*70)


if __name__ == "__main__":
    print("\n" + "🚀 " + "="*68)
    print("PageIndex + pyseekdb 混合RAG系统 - 缓存功能演示")
    print("="*70)

    # 检查API Key
    if not config.openai.api_key or config.openai.api_key == "your_openai_api_key_here":
        print("\n⚠️  请先配置 OPENAI_API_KEY")
        print("   1. 复制 .env.example 为 .env")
        print("   2. 在 .env 中填入你的 OpenAI API Key")
        sys.exit(1)

    # 运行演示
    demo_with_cache()

    print("\n\n")

    demo_without_cache()

    print("\n\n")

    show_performance_comparison()

    print("\n✨ 所有演示完成！")
