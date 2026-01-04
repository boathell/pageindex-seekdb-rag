"""
测试 Qwen-Max API 连接
验证配置是否正确，API 是否可用
"""

from openai import OpenAI
from dotenv import load_dotenv
import os
from loguru import logger

# 加载环境变量
load_dotenv()


def test_qwen_chat():
    """测试 Qwen-Max 聊天 API"""
    logger.info("=" * 70)
    logger.info("测试 Qwen-Max 聊天 API")
    logger.info("=" * 70)

    # 读取配置
    api_key = os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
    model = os.getenv("MODEL_NAME", "qwen-max")
    base_url = os.getenv("BASE_URL")

    logger.info(f"API Key: {api_key[:10]}..." if api_key else "API Key: NOT SET")
    logger.info(f"Model: {model}")
    logger.info(f"Base URL: {base_url}")

    if not api_key:
        logger.error("❌ API_KEY 未设置！")
        return False

    try:
        # 创建客户端
        if base_url:
            client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            client = OpenAI(api_key=api_key)

        # 测试简单的聊天
        logger.info("\n发送测试消息...")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "你好，请用一句话介绍一下什么是存储架构。"}
            ],
            max_tokens=100
        )

        answer = response.choices[0].message.content
        logger.success("\n✓ Qwen-Max 响应成功！")
        logger.info(f"回答: {answer}")

        # 显示使用统计
        if hasattr(response, 'usage'):
            logger.info(f"\nToken 使用情况:")
            logger.info(f"  输入: {response.usage.prompt_tokens}")
            logger.info(f"  输出: {response.usage.completion_tokens}")
            logger.info(f"  总计: {response.usage.total_tokens}")

        return True

    except Exception as e:
        logger.error(f"\n✗ Qwen-Max API 调用失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_qwen_embedding():
    """测试 Qwen embedding API（如果支持）"""
    logger.info("\n" + "=" * 70)
    logger.info("测试 Qwen Embedding API")
    logger.info("=" * 70)

    api_key = os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("BASE_URL")

    # Qwen 可能使用不同的 embedding 模型名称
    embedding_model = "text-embedding-v2"  # Qwen 的 embedding 模型

    try:
        if base_url:
            client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            client = OpenAI(api_key=api_key)

        logger.info(f"尝试使用 embedding 模型: {embedding_model}")

        response = client.embeddings.create(
            model=embedding_model,
            input="测试文本向量化"
        )

        embedding = response.data[0].embedding
        logger.success(f"\n✓ Embedding 成功！向量维度: {len(embedding)}")

        return True, embedding_model

    except Exception as e:
        logger.warning(f"\n⚠ Qwen Embedding API 不可用: {e}")
        logger.info("将使用 OpenAI embedding API 作为备选方案")
        return False, None


def main():
    """主测试流程"""
    logger.info("\n" + "=" * 70)
    logger.info("Qwen-Max API 连接测试")
    logger.info("=" * 70 + "\n")

    # 1. 测试聊天 API
    chat_success = test_qwen_chat()

    # 2. 测试 embedding API
    embedding_success, embedding_model = test_qwen_embedding()

    # 总结
    logger.info("\n" + "=" * 70)
    logger.info("测试结果总结")
    logger.info("=" * 70)

    logger.info(f"聊天 API: {'✓ 正常' if chat_success else '✗ 失败'}")
    logger.info(f"Embedding API: {'✓ 正常' if embedding_success else '⚠ 不可用（将使用 OpenAI）'}")

    if chat_success:
        logger.success("\n✓✓✓ Qwen-Max 配置成功，可以开始使用！✓✓✓")

        if not embedding_success:
            logger.warning("\n⚠ 注意：Embedding 需要使用 OpenAI API")
            logger.info("请确保 .env 中的 OPENAI_API_KEY 和 OPENAI_EMBEDDING_MODEL 已配置")
    else:
        logger.error("\n✗✗✗ Qwen-Max 配置失败，请检查 API_KEY 和 BASE_URL ✗✗✗")

    logger.info("=" * 70 + "\n")


if __name__ == "__main__":
    main()
