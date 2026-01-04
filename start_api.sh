#!/bin/bash
# API 服务启动脚本

echo "========================================="
echo "PageIndex + seekdb RAG API Server"
echo "========================================="
echo

# 检查 seekdb 是否运行
echo "检查 seekdb 状态..."
if docker ps | grep -q seekdb; then
    echo "✓ seekdb 容器正在运行"
else
    echo "⚠ seekdb 容器未运行，正在启动..."
    docker-compose up -d seekdb
    echo "等待 seekdb 启动完成..."
    sleep 10
fi
echo

# 检查环境配置
if [ ! -f .env ]; then
    echo "⚠ .env 文件不存在，从示例复制..."
    cp .env.example .env
    echo "请编辑 .env 文件，填入您的 API Key"
    exit 1
fi
echo "✓ .env 配置文件存在"
echo

# 启动 API 服务
echo "启动 API 服务..."
echo "访问地址:"
echo "  - API 文档 (Swagger): http://localhost:8000/docs"
echo "  - API 文档 (ReDoc):  http://localhost:8000/redoc"
echo "  - 健康检查:           http://localhost:8000/health"
echo
python -m uvicorn src.api_server:app --reload --host 0.0.0.0 --port 8000
