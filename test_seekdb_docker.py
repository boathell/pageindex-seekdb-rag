"""
测试 seekdb Docker 部署
验证连接、数据库创建和基本操作
"""

import pyseekdb
import numpy as np
from loguru import logger

def test_seekdb_connection():
    """测试 seekdb 连接"""
    logger.info("=" * 60)
    logger.info("测试 1: 连接到 seekdb Docker 服务器并创建数据库")
    logger.info("=" * 60)

    try:
        # 首先连接到系统数据库（不指定 database）
        import pymysql

        logger.info("连接到系统数据库...")
        conn = pymysql.connect(
            host="127.0.0.1",
            port=2881,
            user="root",
            password=""
        )
        cursor = conn.cursor()

        # 创建数据库（如果不存在）
        logger.info("创建数据库 test_db...")
        cursor.execute("CREATE DATABASE IF NOT EXISTS test_db")
        cursor.execute("SHOW DATABASES")
        databases = cursor.fetchall()
        logger.info(f"当前数据库列表: {[db[0] for db in databases]}")

        cursor.close()
        conn.close()
        logger.success("✓ 数据库创建成功")

        # 连接到新创建的数据库
        logger.info("连接到 test_db 数据库...")
        client = pyseekdb.Client(
            host="127.0.0.1",
            port=2881,
            database="test_db",
            user="root",
            password=""
        )
        logger.success("✓ 成功连接到 seekdb 服务器和 test_db 数据库")
        return client
    except Exception as e:
        logger.error(f"✗ 连接失败: {e}")
        raise


def test_create_collection(client):
    """测试创建 Collection"""
    logger.info("=" * 60)
    logger.info("测试 2: 创建 Collection")
    logger.info("=" * 60)

    collection_name = "test_collection"
    embedding_dims = 384  # 使用 seekdb 默认维度

    try:
        # 先尝试删除旧的 collection（如果存在）
        try:
            client.delete_collection(name=collection_name)
            logger.info(f"删除了旧的 collection: {collection_name}")
        except Exception:
            pass  # collection 不存在，忽略

        # 创建新的 collection
        client.create_collection(
            name=collection_name,
            embedding_model_dims=embedding_dims,
            description="测试用的 collection"
        )
        logger.success(f"✓ 成功创建 collection: {collection_name} ({embedding_dims}维)")
    except Exception as e:
        logger.error(f"✗ 创建 collection 失败: {e}")
        raise

    # 获取 collection
    collection = client.get_collection(collection_name)
    logger.success(f"✓ 成功获取 collection: {collection_name}")

    return collection, embedding_dims


def test_insert_data(collection, embedding_dims):
    """测试插入数据"""
    logger.info("=" * 60)
    logger.info("测试 3: 插入向量数据")
    logger.info("=" * 60)

    # 准备测试数据
    ids = ["doc1", "doc2", "doc3"]
    documents = [
        "人工智能是计算机科学的一个分支",
        "机器学习是实现人工智能的一种方法",
        "深度学习使用神经网络进行学习"
    ]
    embeddings = [
        np.random.rand(embedding_dims).tolist(),
        np.random.rand(embedding_dims).tolist(),
        np.random.rand(embedding_dims).tolist()
    ]
    metadatas = [
        {"category": "AI", "year": 2024},
        {"category": "ML", "year": 2024},
        {"category": "DL", "year": 2024}
    ]

    try:
        # 插入数据 - 使用正确的 API 格式
        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )
        logger.success(f"✓ 成功插入 {len(ids)} 条数据")
    except Exception as e:
        logger.error(f"✗ 插入数据失败: {e}")
        raise


def test_query_data(collection, embedding_dims):
    """测试查询数据"""
    logger.info("=" * 60)
    logger.info("测试 4: 向量检索")
    logger.info("=" * 60)

    # 生成查询向量
    query_embedding = np.random.rand(embedding_dims).tolist()

    try:
        # 执行向量检索
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=2
        )

        logger.success("✓ 向量检索成功")
        logger.info(f"返回结果数: {len(results['ids'][0])}")

        # 显示结果
        for i, doc_id in enumerate(results['ids'][0]):
            logger.info(f"  结果 {i+1}:")
            logger.info(f"    ID: {doc_id}")
            logger.info(f"    文档: {results['documents'][0][i]}")
            logger.info(f"    距离: {results['distances'][0][i]:.4f}")
            logger.info(f"    元数据: {results['metadatas'][0][i]}")

        return results
    except Exception as e:
        logger.error(f"✗ 查询失败: {e}")
        raise


def test_get_data(collection):
    """测试获取数据"""
    logger.info("=" * 60)
    logger.info("测试 5: 获取指定数据")
    logger.info("=" * 60)

    try:
        # 获取所有数据
        results = collection.get()

        logger.success(f"✓ 成功获取数据")
        logger.info(f"总文档数: {len(results['ids'])}")

        return results
    except Exception as e:
        logger.error(f"✗ 获取数据失败: {e}")
        raise


def test_count(collection):
    """测试统计数据量"""
    logger.info("=" * 60)
    logger.info("测试 6: 统计数据量")
    logger.info("=" * 60)

    try:
        count = collection.count()
        logger.success(f"✓ Collection 中共有 {count} 条数据")
        return count
    except Exception as e:
        logger.error(f"✗ 统计失败: {e}")
        raise


def test_delete_data(collection):
    """测试删除数据"""
    logger.info("=" * 60)
    logger.info("测试 7: 删除数据")
    logger.info("=" * 60)

    try:
        # 删除一条数据
        collection.delete(ids=["doc1"])
        logger.success("✓ 成功删除数据 doc1")

        # 验证删除
        count = collection.count()
        logger.info(f"删除后剩余数据: {count} 条")

    except Exception as e:
        logger.error(f"✗ 删除失败: {e}")
        raise


def main():
    """主测试流程"""
    logger.info("\n" + "=" * 60)
    logger.info("开始 seekdb Docker 部署测试")
    logger.info("=" * 60 + "\n")

    try:
        # 1. 连接测试
        client = test_seekdb_connection()

        # 2. 创建 collection
        collection, embedding_dims = test_create_collection(client)

        # 3. 插入数据
        test_insert_data(collection, embedding_dims)

        # 4. 查询数据
        test_query_data(collection, embedding_dims)

        # 5. 获取数据
        test_get_data(collection)

        # 6. 统计数据
        test_count(collection)

        # 7. 删除数据
        test_delete_data(collection)

        logger.info("\n" + "=" * 60)
        logger.success("✓✓✓ 所有测试通过！seekdb Docker 部署正常工作 ✓✓✓")
        logger.info("=" * 60 + "\n")

    except Exception as e:
        logger.error("\n" + "=" * 60)
        logger.error(f"✗✗✗ 测试失败: {e} ✗✗✗")
        logger.error("=" * 60 + "\n")
        raise


if __name__ == "__main__":
    main()
