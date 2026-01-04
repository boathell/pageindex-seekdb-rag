"""
缓存功能测试示例
演示如何使用CacheManager提升检索性能
"""

import sys
import os
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pyseekdb
# 直接导入，避免触发config初始化
import sys
sys.path.insert(0, str(project_root / "src"))
from cache_manager import CacheManager
from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stderr, level="INFO")


def test_cache_manager():
    """测试缓存管理器基本功能"""
    print("\n" + "="*60)
    print("测试 CacheManager 基本功能")
    print("="*60)

    # 1. 创建pyseekdb客户端（嵌入式模式）
    data_dir = project_root / "data" / "pyseekdb_test"
    data_dir.mkdir(parents=True, exist_ok=True)

    client = pyseekdb.Client(
        path=str(data_dir),
        database="test_cache"
    )
    cache_manager = CacheManager(client, ttl=900, enable_cache=True)

    # 2. 模拟检索结果
    test_query = "什么是混合RAG系统？"
    mock_results = [
        {
            "chunk_id": "chunk_001",
            "content": "混合RAG系统结合了树结构检索和向量检索",
            "score": 0.95,
            "node_id": "node_001",
            "node_path": ["根节点", "第一章", "1.1节"],
            "page_num": 5,
            "metadata": {}
        },
        {
            "chunk_id": "chunk_002",
            "content": "PageIndex提供结构化推理能力",
            "score": 0.88,
            "node_id": "node_002",
            "node_path": ["根节点", "第一章", "1.2节"],
            "page_num": 7,
            "metadata": {}
        }
    ]

    # 3. 测试查询缓存
    print("\n[1] 测试查询缓存")
    print("-" * 60)

    # 第一次查询 - 缓存未命中
    print("第一次查询（应该未命中）...")
    start = time.time()
    cached = cache_manager.get_query_cache(test_query, document_id="doc_001")
    elapsed = time.time() - start
    print(f"  结果: {cached}")
    print(f"  耗时: {elapsed*1000:.2f}ms")

    # 设置缓存
    print("\n保存查询结果到缓存...")
    cache_manager.set_query_cache(
        query=test_query,
        results=mock_results,
        document_id="doc_001",
        strategy="hybrid"
    )

    # 第二次查询 - 缓存命中
    print("\n第二次查询（应该命中）...")
    start = time.time()
    cached = cache_manager.get_query_cache(test_query, document_id="doc_001")
    elapsed = time.time() - start
    print(f"  结果: {'命中' if cached else '未命中'}")
    print(f"  耗时: {elapsed*1000:.2f}ms")
    if cached:
        print(f"  返回条目数: {len(cached)}")

    # 4. 测试树缓存
    print("\n[2] 测试文档树缓存")
    print("-" * 60)

    mock_tree = {
        "root": {
            "title": "测试文档",
            "children": [
                {"title": "第一章", "children": []},
                {"title": "第二章", "children": []}
            ]
        }
    }

    # 保存树缓存
    print("保存文档树到缓存...")
    cache_manager.set_tree_cache("doc_001", mock_tree)

    # 获取树缓存
    print("从缓存获取文档树...")
    cached_tree = cache_manager.get_tree_cache("doc_001")
    print(f"  结果: {'命中' if cached_tree else '未命中'}")
    if cached_tree:
        print(f"  根节点标题: {cached_tree['root']['title']}")

    # 5. 获取缓存统计
    print("\n[3] 缓存统计信息")
    print("-" * 60)
    stats = cache_manager.get_cache_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # 6. 测试过期清理
    print("\n[4] 测试缓存清理")
    print("-" * 60)

    # 测试清理所有缓存
    print("清理所有缓存...")
    cleared = cache_manager.clear_all_cache()
    print(f"  清理了 {cleared} 条缓存")

    # 再次查询应该未命中
    print("\n清理后查询（应该未命中）...")
    cached = cache_manager.get_query_cache(test_query, document_id="doc_001")
    print(f"  结果: {'命中' if cached else '未命中'}")

    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)


def test_cache_with_disabled():
    """测试禁用缓存的情况"""
    print("\n" + "="*60)
    print("测试禁用缓存")
    print("="*60)

    data_dir = project_root / "data" / "pyseekdb_test"
    client = pyseekdb.Client(
        path=str(data_dir),
        database="test_cache"
    )

    # 创建禁用缓存的管理器
    cache_manager = CacheManager(client, enable_cache=False)

    # 尝试获取缓存（应该返回None）
    result = cache_manager.get_query_cache("测试查询")
    print(f"禁用缓存时查询结果: {result}")

    # 尝试设置缓存（应该不做任何事）
    cache_manager.set_query_cache("测试查询", [{"test": "data"}])
    print("设置缓存操作完成（实际未保存）")

    # 获取统计信息
    stats = cache_manager.get_cache_stats()
    print(f"统计信息: {stats}")

    print("\n测试完成！")


if __name__ == "__main__":
    # 运行测试
    test_cache_manager()

    print("\n\n")

    test_cache_with_disabled()
