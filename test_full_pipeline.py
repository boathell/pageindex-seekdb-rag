"""
完整的 PageIndex + seekdb RAG 系统端到端测试
测试流程：
1. 使用 PageIndex 解析 PDF
2. 将数据索引到 seekdb Docker
3. 执行混合检索测试
4. 对比三种检索策略
"""

import sys
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv
import os

# 添加项目路径到 sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.document_indexer import DocumentIndexer
from src.hybrid_search import HybridSearchEngine
from src.seekdb_manager import SeekDBManager
from src.embedding_manager import EmbeddingManager
from src.config import config

# 加载环境变量
load_dotenv()


def check_prerequisites():
    """检查前置条件"""
    logger.info("=" * 70)
    logger.info("检查前置条件")
    logger.info("=" * 70)

    issues = []

    # 检查 API Key（优先使用 API_KEY，否则使用 OPENAI_API_KEY）
    api_key = os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_openai_api_key_here":
        issues.append("❌ API_KEY 或 OPENAI_API_KEY 未设置")
        logger.error("请在 .env 文件中设置有效的 API_KEY 或 OPENAI_API_KEY")
    else:
        logger.success(f"✓ API Key 已设置: {api_key[:10]}...")

    # 显示使用的 API 端点
    base_url = os.getenv("BASE_URL")
    model_name = os.getenv("MODEL_NAME") or os.getenv("OPENAI_MODEL")
    if base_url:
        logger.info(f"✓ 使用自定义 API: {base_url}")
        logger.info(f"✓ 使用模型: {model_name}")
    else:
        logger.info(f"✓ 使用 OpenAI API")

    # 检查 seekdb Docker
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=seekdb", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            check=True
        )
        if "Up" in result.stdout:
            logger.success("✓ seekdb Docker 容器正在运行")
        else:
            issues.append("❌ seekdb Docker 容器未运行")
            logger.error("请运行: docker-compose up -d")
    except Exception as e:
        issues.append(f"❌ 无法检查 Docker 状态: {e}")
        logger.error(f"Docker 检查失败: {e}")

    # 检查 PDF 文件
    pdf_path = Path("data/1282-1311_存储架构.pdf")
    if pdf_path.exists():
        logger.success(f"✓ PDF 文件存在: {pdf_path} ({pdf_path.stat().st_size / 1024:.1f} KB)")
    else:
        issues.append(f"❌ PDF 文件不存在: {pdf_path}")
        logger.error(f"找不到 PDF 文件: {pdf_path}")

    # 检查 PageIndex
    pageindex_script = project_root / "external" / "PageIndex" / "run_pageindex.py"
    if pageindex_script.exists():
        logger.success(f"✓ PageIndex 脚本存在: {pageindex_script}")
    else:
        issues.append(f"❌ PageIndex 脚本不存在: {pageindex_script}")
        logger.error(f"找不到 PageIndex 脚本: {pageindex_script}")

    if issues:
        logger.error("\n" + "=" * 70)
        logger.error("发现以下问题:")
        for issue in issues:
            logger.error(f"  {issue}")
        logger.error("=" * 70)
        return False

    logger.success("\n" + "=" * 70)
    logger.success("✓✓✓ 所有前置条件检查通过 ✓✓✓")
    logger.success("=" * 70 + "\n")
    return True


def test_document_indexing():
    """测试文档索引流程"""
    logger.info("\n" + "=" * 70)
    logger.info("步骤 1: 文档索引（PageIndex + seekdb）")
    logger.info("=" * 70)

    pdf_path = "data/1282-1311_存储架构.pdf"
    document_id = "storage_architecture"

    try:
        # 创建索引器
        logger.info("初始化 DocumentIndexer...")
        logger.info(f"使用 API: {config.openai.base_url or 'OpenAI'}")
        logger.info(f"使用模型: {config.openai.get_model()}")

        # 准备 PageIndex 配置
        pageindex_config = {
            "model": config.pageindex.pageindex_model,
            "toc_check_pages": config.pageindex.pageindex_toc_check_pages,
            "max_pages_per_node": config.pageindex.pageindex_max_pages_per_node,
            "max_tokens_per_node": config.pageindex.pageindex_max_tokens_per_node
        }

        indexer = DocumentIndexer(
            openai_api_key=config.openai.get_api_key(),
            seekdb_mode=config.seekdb.seekdb_mode,
            persist_directory=config.seekdb.seekdb_persist_dir,
            seekdb_host=config.seekdb.seekdb_host,
            seekdb_port=config.seekdb.seekdb_port,
            seekdb_user=config.seekdb.seekdb_user,
            seekdb_password=config.seekdb.seekdb_password,
            seekdb_database=config.seekdb.seekdb_database,
            pageindex_config=pageindex_config,
            embedding_model=config.openai.openai_embedding_model,
            embedding_base_url=config.openai.base_url,
            embedding_dims=config.seekdb.embedding_dims,
            chunk_size=config.search.chunk_size,
            chunk_overlap=config.search.chunk_overlap
        )

        logger.info(f"开始索引文档: {pdf_path}")
        logger.info(f"文档 ID: {document_id}")
        logger.info("这个过程可能需要几分钟，请耐心等待...")

        # 执行索引
        result = indexer.index_document(
            pdf_path=pdf_path,
            document_id=document_id,
            metadata={"source": "storage_architecture_tutorial", "type": "technical"}
        )

        logger.success("\n" + "-" * 70)
        logger.success("✓ 文档索引完成!")
        logger.info(f"  总节点数: {result['total_nodes']}")
        logger.info(f"  总内容块数: {result['total_chunks']}")
        logger.info(f"  文档页数: {result.get('total_pages', 'N/A')}")
        logger.success("-" * 70)

        return True, document_id

    except Exception as e:
        logger.error(f"\n✗ 文档索引失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False, None


def test_hybrid_search(document_id: str):
    """测试混合检索"""
    logger.info("\n" + "=" * 70)
    logger.info("步骤 2: 混合检索测试")
    logger.info("=" * 70)

    try:
        # 初始化组件
        logger.info("初始化检索引擎...")

        db_manager = SeekDBManager(
            mode=config.seekdb.seekdb_mode,
            persist_directory=config.seekdb.seekdb_persist_dir,
            host=config.seekdb.seekdb_host,
            port=config.seekdb.seekdb_port,
            user=config.seekdb.seekdb_user,
            password=config.seekdb.seekdb_password,
            database=config.seekdb.seekdb_database
        )

        embed_manager = EmbeddingManager(
            api_key=config.openai.get_api_key(),
            model=config.openai.openai_embedding_model,
            base_url=config.openai.base_url
        )

        search_engine = HybridSearchEngine(
            seekdb_manager=db_manager,
            embedding_manager=embed_manager
        )

        # 测试查询
        test_queries = [
            "什么是存储架构？",
            "数据库存储的主要组件有哪些？",
            "如何优化存储性能？"
        ]

        logger.info(f"\n测试 {len(test_queries)} 个查询...\n")

        for i, query in enumerate(test_queries, 1):
            logger.info("-" * 70)
            logger.info(f"查询 {i}: {query}")
            logger.info("-" * 70)

            # 执行混合检索
            results = search_engine.hybrid_search(
                query=query,
                document_id=document_id,
                strategy="hybrid",
                top_k=3
            )

            logger.info(f"返回 {len(results)} 条结果:\n")

            for j, result in enumerate(results, 1):
                logger.info(f"  结果 {j}:")
                logger.info(f"    分数: {result.score:.4f}")
                logger.info(f"    路径: {' > '.join(result.node_path[:3])}{'...' if len(result.node_path) > 3 else ''}")
                logger.info(f"    页码: {result.page_num}")
                logger.info(f"    内容预览: {result.content[:150]}...")
                logger.info("")

        logger.success("\n" + "-" * 70)
        logger.success("✓ 混合检索测试完成!")
        logger.success("-" * 70)

        return True, search_engine

    except Exception as e:
        logger.error(f"\n✗ 混合检索测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False, None


def test_strategy_comparison(search_engine, document_id: str):
    """对比三种检索策略"""
    logger.info("\n" + "=" * 70)
    logger.info("步骤 3: 检索策略对比")
    logger.info("=" * 70)

    try:
        query = "存储架构的核心设计原则是什么？"
        strategies = ["tree_only", "vector_only", "hybrid"]

        logger.info(f"\n测试查询: {query}\n")

        results_by_strategy = {}

        for strategy in strategies:
            logger.info("-" * 70)
            logger.info(f"策略: {strategy.upper()}")
            logger.info("-" * 70)

            results = search_engine.hybrid_search(
                query=query,
                document_id=document_id,
                strategy=strategy,
                top_k=5
            )

            results_by_strategy[strategy] = results

            logger.info(f"返回结果数: {len(results)}")
            if results:
                logger.info(f"最高分数: {results[0].score:.4f}")
                logger.info(f"最低分数: {results[-1].score:.4f}")
                logger.info(f"平均分数: {sum(r.score for r in results) / len(results):.4f}")
            logger.info("")

        # 对比总结
        logger.info("\n" + "=" * 70)
        logger.info("策略对比总结")
        logger.info("=" * 70)

        logger.info(f"\n{'策略':<15} {'结果数':<10} {'最高分':<10} {'平均分':<10}")
        logger.info("-" * 50)

        for strategy in strategies:
            results = results_by_strategy[strategy]
            if results:
                logger.info(
                    f"{strategy:<15} {len(results):<10} "
                    f"{results[0].score:<10.4f} "
                    f"{sum(r.score for r in results) / len(results):<10.4f}"
                )
            else:
                logger.info(f"{strategy:<15} {'0':<10} {'-':<10} {'-':<10}")

        logger.success("\n" + "-" * 70)
        logger.success("✓ 策略对比完成!")
        logger.success("-" * 70)

        return True

    except Exception as e:
        logger.error(f"\n✗ 策略对比失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """主测试流程"""
    logger.info("\n" + "=" * 70)
    logger.info("PageIndex + seekdb 混合 RAG 系统 - 完整测试")
    logger.info("=" * 70)
    logger.info(f"PDF 文件: data/1282-1311_存储架构.pdf")
    logger.info(f"seekdb 模式: {config.seekdb.seekdb_mode}")
    logger.info(f"Embedding 模型: {config.openai.openai_embedding_model}")
    logger.info("=" * 70 + "\n")

    # 1. 检查前置条件
    if not check_prerequisites():
        logger.error("\n前置条件检查失败，请修复上述问题后重试")
        return

    # 2. 文档索引
    success, document_id = test_document_indexing()
    if not success:
        logger.error("\n文档索引失败，终止测试")
        return

    # 3. 混合检索测试
    success, search_engine = test_hybrid_search(document_id)
    if not success:
        logger.error("\n混合检索测试失败，终止测试")
        return

    # 4. 策略对比
    success = test_strategy_comparison(search_engine, document_id)
    if not success:
        logger.error("\n策略对比失败")
        return

    # 完成
    logger.info("\n" + "=" * 70)
    logger.success("✓✓✓ 所有测试完成! ✓✓✓")
    logger.success("PageIndex + seekdb 混合 RAG 系统运行正常!")
    logger.info("=" * 70 + "\n")


if __name__ == "__main__":
    main()
