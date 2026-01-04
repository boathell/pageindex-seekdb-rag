# PageIndex + seekdb RAG 系统部署指南

本文档详细说明如何部署 PageIndex + seekdb 混合 RAG 系统。

## 目录
- [系统要求](#系统要求)
- [seekdb 部署](#seekdb-部署)
- [配置说明](#配置说明)
- [测试验证](#测试验证)
- [常见问题](#常见问题)

## 系统要求

### 硬件要求
- **CPU**: 4核以上推荐
- **内存**: 8GB 以上推荐
- **磁盘**: 10GB 以上可用空间

### 软件要求
- **操作系统**: Linux / macOS / Windows (WSL2)
- **Python**: 3.10 或更高版本
- **Docker**: 20.10 或更高版本（Server 模式）
- **Docker Compose**: 2.0 或更高版本（Server 模式）

## seekdb 部署

### 方式一：Docker Compose 部署（推荐）

#### 1. 检查 docker-compose.yml

确保项目根目录有 `docker-compose.yml` 文件：

```yaml
version: '3.8'

services:
  seekdb:
    image: oceanbase/seekdb:latest
    container_name: seekdb
    ports:
      - "2881:2881"  # SQL 端口
      - "2886:2886"  # RPC 端口
    volumes:
      - ./data/seekdb:/var/lib/oceanbase
    restart: unless-stopped
    environment:
      - MODE=slim
    healthcheck:
      test: ["CMD", "mysql", "-h", "127.0.0.1", "-P", "2881", "-uroot", "-e", "SELECT 1"]
      interval: 30s
      timeout: 10s
      retries: 5
```

#### 2. 启动服务

```bash
# 启动 seekdb 服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f seekdb

# 等待服务完全启动（约 30-60 秒）
sleep 60
```

#### 3. 验证连接

```bash
# 测试 MySQL 连接
docker exec -it seekdb mysql -h127.0.0.1 -P2881 -uroot -e "SELECT VERSION();"
```

预期输出类似：
```
+-----------+
| VERSION() |
+-----------+
| 8.0.32    |
+-----------+
```

#### 4. 创建数据库

```bash
# 进入 MySQL 客户端
docker exec -it seekdb mysql -h127.0.0.1 -P2881 -uroot

# 在 MySQL 中执行
CREATE DATABASE IF NOT EXISTS rag_system;
SHOW DATABASES;
EXIT;
```

### 方式二：直接使用 Docker

```bash
# 拉取镜像
docker pull oceanbase/seekdb:latest

# 启动容器
docker run -d \
  --name seekdb \
  -p 2881:2881 \
  -p 2886:2886 \
  -v $(pwd)/data/seekdb:/var/lib/oceanbase \
  --restart unless-stopped \
  oceanbase/seekdb:latest

# 查看日志
docker logs -f seekdb

# 等待启动完成
sleep 60

# 创建数据库
docker exec -it seekdb mysql -h127.0.0.1 -P2881 -uroot -e "CREATE DATABASE IF NOT EXISTS rag_system;"
```

### 方式三：Embedded 模式（无需 Docker）

如果不想使用 Docker，可以使用 pyseekdb 的 Embedded 模式：

```bash
# 在 .env 文件中配置
SEEKDB_MODE=embedded
SEEKDB_PERSIST_DIR=./data/pyseekdb
```

数据将存储在本地文件系统，无需运行 Docker 容器。

## 配置说明

### 环境变量配置

#### 1. 复制配置模板

```bash
cp .env.example .env
```

#### 2. 选择 API 提供商

**选项 A：使用 OpenAI API**

```bash
# .env 文件
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-2024-11-20
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

**选项 B：使用 Qwen-Max API（推荐国内用户）**

```bash
# .env 文件
# 主配置
API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
MODEL_NAME=qwen-max
BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# Embedding 配置
OPENAI_EMBEDDING_MODEL=text-embedding-v2

# PageIndex 配置
PAGEINDEX_MODEL=qwen-max
```

> **获取 Qwen API Key**: https://dashscope.console.aliyun.com/apiKey

#### 3. seekdb 配置

**Server 模式（Docker）**:
```bash
SEEKDB_MODE=server
SEEKDB_HOST=127.0.0.1
SEEKDB_PORT=2881
SEEKDB_USER=root
SEEKDB_PASSWORD=
SEEKDB_DATABASE=rag_system
EMBEDDING_DIMS=1536
```

**Embedded 模式**:
```bash
SEEKDB_MODE=embedded
SEEKDB_PERSIST_DIR=./data/pyseekdb
EMBEDDING_DIMS=1536
```

#### 4. 其他配置

```bash
# 检索配置
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K_CHUNKS=20

# PageIndex 配置
PAGEINDEX_TOC_CHECK_PAGES=20
PAGEINDEX_MAX_PAGES_PER_NODE=10
PAGEINDEX_MAX_TOKENS_PER_NODE=20000
```

### 向量维度说明

不同的 embedding 模型使用不同的向量维度：

| Embedding 模型 | 维度 | 配置值 |
|--------------|------|--------|
| text-embedding-3-small | 1536 | `EMBEDDING_DIMS=1536` |
| text-embedding-3-large | 3072 | `EMBEDDING_DIMS=3072` |
| text-embedding-v2 (Qwen) | 1536 | `EMBEDDING_DIMS=1536` |
| text-embedding-ada-002 | 1536 | `EMBEDDING_DIMS=1536` |

⚠️ **重要**: `EMBEDDING_DIMS` 必须与你选择的 embedding 模型维度匹配！

## 测试验证

### 1. 运行完整测试

```bash
# 激活虚拟环境
source venv/bin/activate  # Windows: venv\Scripts\activate

# 运行测试脚本
python test_full_pipeline.py
```

预期输出：
```
======================================================================
✓✓✓ 所有前置条件检查通过 ✓✓✓
======================================================================

步骤 1: 文档索引（PageIndex + seekdb）
✓ 文档索引完成!
  总节点数: 40
  总内容块数: 150
  文档页数: 30
```

### 2. 验证数据库

```python
# 运行 Python 脚本检查数据
python3 << 'EOF'
import pymysql

conn = pymysql.connect(
    host="127.0.0.1",
    port=2881,
    user="root",
    password="",
    database="rag_system"
)

cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM `c$v1$tree_nodes`")
nodes_count = cursor.fetchone()[0]
print(f"✓ Tree nodes: {nodes_count}")

cursor.execute("DESCRIBE `c$v1$tree_nodes`")
for col in cursor.fetchall():
    if 'embedding' in col[0].lower():
        print(f"✓ Vector dimension: {col[1]}")

cursor.close()
conn.close()
EOF
```

### 3. 简单检索测试

```python
from src.hybrid_search import HybridSearchEngine
from src.seekdb_manager import SeekDBManager
from src.embedding_manager import EmbeddingManager
from src.config import config

# 初始化
db = SeekDBManager(
    mode=config.seekdb.seekdb_mode,
    host=config.seekdb.seekdb_host,
    port=config.seekdb.seekdb_port,
    database=config.seekdb.seekdb_database
)

embed = EmbeddingManager(
    api_key=config.openai.get_api_key(),
    model=config.openai.openai_embedding_model,
    base_url=config.openai.base_url
)

engine = HybridSearchEngine(db, embed)

# 测试检索
results = engine.hybrid_search(
    query="系统的主要功能是什么？",
    document_id="storage_architecture",
    strategy="hybrid",
    top_k=3
)

print(f"✓ 检索返回 {len(results)} 条结果")
```

## 常见问题

### Q1: Docker 容器启动失败

**问题**: `docker-compose up -d` 失败或容器反复重启

**解决方案**:
```bash
# 查看详细日志
docker-compose logs seekdb

# 检查端口占用
lsof -i :2881
lsof -i :2886

# 清理并重新启动
docker-compose down -v
docker-compose up -d
```

### Q2: 向量维度不匹配错误

**错误信息**: `inconsistent dimension: expected 384 got 1536`

**原因**: seekdb collection 创建时使用了错误的维度

**解决方案**:
```python
# 删除并重建数据库
import pymysql
conn = pymysql.connect(host="127.0.0.1", port=2881, user="root", password="")
cursor = conn.cursor()
cursor.execute("DROP DATABASE IF EXISTS rag_system")
cursor.execute("CREATE DATABASE rag_system")
conn.commit()

# 确保 .env 中配置正确
# EMBEDDING_DIMS=1536
```

### Q3: Qwen API 批量限制错误

**错误信息**: `batch size is invalid, it should not be larger than 25`

**原因**: Qwen embedding API 单次最多支持 25 个文本

**解决方案**: 代码已自动处理分批，如果仍有问题，检查 EmbeddingManager 配置：
```python
# src/embedding_manager.py
batch_size = 25  # 确保不超过 25
```

### Q4: PageIndex 输出文件找不到

**错误信息**: `PageIndex output file not found`

**原因**: PageIndex 输出路径变化

**解决方案**: 代码已支持多路径搜索，确保：
1. PageIndex 正常执行完成
2. `external/PageIndex/results/` 目录可写
3. 检查 PageIndex 日志输出

### Q5: 内存不足

**问题**: 大文档处理时内存溢出

**解决方案**:
```bash
# 调整 Docker 内存限制
# docker-compose.yml
services:
  seekdb:
    mem_limit: 4g

# 或减小批处理大小
# .env
CHUNK_SIZE=300
TOP_K_CHUNKS=10
```

## 性能调优

### 1. seekdb 性能优化

```bash
# 增加缓存大小（在 seekdb 容器内）
docker exec -it seekdb mysql -h127.0.0.1 -P2881 -uroot -e "
SET GLOBAL innodb_buffer_pool_size=2GB;
"
```

### 2. embedding 批处理优化

```python
# src/embedding_manager.py
# 调整批处理大小
batch_size = 20  # Qwen 建议 < 25
```

### 3. 并发控制

```python
# 控制并发 API 调用
import asyncio
semaphore = asyncio.Semaphore(5)  # 最多 5 个并发请求
```

## 监控和维护

### 1. 查看 seekdb 状态

```bash
# 容器状态
docker stats seekdb

# 数据库状态
docker exec -it seekdb mysql -h127.0.0.1 -P2881 -uroot -e "SHOW STATUS;"
```

### 2. 数据备份

```bash
# 备份数据目录
tar -czf seekdb_backup_$(date +%Y%m%d).tar.gz ./data/seekdb/

# 导出数据库
docker exec seekdb mysqldump -h127.0.0.1 -P2881 -uroot rag_system > backup.sql
```

### 3. 清理旧数据

```python
# 删除特定文档的所有数据
from src.seekdb_manager import SeekDBManager

db = SeekDBManager(mode="server", database="rag_system")
stats = db.delete_document("document_id_to_delete")
print(f"Deleted {stats['nodes_deleted']} nodes, {stats['chunks_deleted']} chunks")
```

---

如有问题，请提交 Issue: https://github.com/yourusername/pageindex-seekdb-rag/issues
