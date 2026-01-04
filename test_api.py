"""
API 测试脚本
测试 FastAPI 服务的各个端点
"""

import requests
import json
from pathlib import Path
from loguru import logger

# API 基础URL
BASE_URL = "http://localhost:8000"

def test_health():
    """测试健康检查"""
    logger.info("Testing /health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    assert response.status_code == 200
    logger.success("✓ Health check passed")
    print()


def test_root():
    """测试根路径"""
    logger.info("Testing / endpoint...")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    assert response.status_code == 200
    logger.success("✓ Root endpoint passed")
    print()


def test_index_document():
    """测试文档索引"""
    logger.info("Testing /index endpoint...")

    # 使用测试 PDF
    pdf_path = "data/1282-1311_存储架构.pdf"

    if not Path(pdf_path).exists():
        logger.warning(f"PDF file not found: {pdf_path}, skipping index test")
        return

    data = {
        "document_id": "test_storage_architecture",
        "pdf_path": pdf_path
    }

    response = requests.post(
        f"{BASE_URL}/index",
        json=data,
        timeout=600  # 索引可能需要较长时间
    )

    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))

    if response.status_code == 200:
        logger.success("✓ Document indexed successfully")
    else:
        logger.error(f"✗ Index failed: {response.text}")
    print()


def test_search():
    """测试混合检索"""
    logger.info("Testing /search endpoint...")

    # 测试不同的检索策略
    strategies = ["hybrid", "tree_only", "vector_only"]

    for strategy in strategies:
        logger.info(f"Testing strategy: {strategy}")

        data = {
            "query": "什么是LSM-Tree存储架构？",
            "document_id": "test_storage_architecture",
            "strategy": strategy,
            "top_k": 3
        }

        response = requests.post(
            f"{BASE_URL}/search",
            json=data
        )

        print(f"Strategy: {strategy}")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"Total results: {result['total_results']}")

            for i, item in enumerate(result['results'][:2], 1):
                print(f"\n  Result {i}:")
                print(f"    Score: {item['score']:.4f}")
                print(f"    Path: {' > '.join(item['node_path'])}")
                print(f"    Page: {item['page_num']}")
                print(f"    Content: {item['content'][:100]}...")

            logger.success(f"✓ Search with {strategy} passed")
        else:
            logger.error(f"✗ Search failed: {response.text}")

        print()


def test_list_documents():
    """测试列出文档"""
    logger.info("Testing /documents endpoint...")

    response = requests.get(f"{BASE_URL}/documents")

    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Total documents: {result['total_documents']}")
    print(json.dumps(result['documents'], indent=2, ensure_ascii=False))

    if response.status_code == 200:
        logger.success("✓ List documents passed")
    else:
        logger.error(f"✗ List failed: {response.text}")
    print()


def test_stats():
    """测试统计信息"""
    logger.info("Testing /stats endpoint...")

    response = requests.get(f"{BASE_URL}/stats")

    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))

    if response.status_code == 200:
        logger.success("✓ Stats passed")
    else:
        logger.error(f"✗ Stats failed: {response.text}")
    print()


def test_delete_document():
    """测试删除文档"""
    logger.info("Testing DELETE /documents/{id} endpoint...")

    document_id = "test_storage_architecture"

    response = requests.delete(f"{BASE_URL}/documents/{document_id}")

    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))

    if response.status_code == 200:
        logger.success("✓ Delete document passed")
    else:
        logger.error(f"✗ Delete failed: {response.text}")
    print()


def main():
    """运行所有测试"""
    logger.info("=" * 70)
    logger.info("API 测试开始")
    logger.info("=" * 70)
    print()

    try:
        # 1. 基础测试
        test_root()
        test_health()
        test_stats()

        # 2. 文档操作测试
        test_index_document()
        test_list_documents()

        # 3. 检索测试
        test_search()

        # 4. 清理测试（可选，注释掉避免删除数据）
        # test_delete_document()

        logger.info("=" * 70)
        logger.success("所有测试完成！")
        logger.info("=" * 70)

    except requests.exceptions.ConnectionError:
        logger.error("无法连接到 API 服务器！")
        logger.error("请确保服务器正在运行：")
        logger.error("  python -m uvicorn src.api_server:app --reload")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
