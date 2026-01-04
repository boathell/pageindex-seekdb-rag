# API 接口文档

PageIndex + seekdb 混合 RAG 系统的 RESTful API 接口说明。

## 📋 目录

- [快速开始](#快速开始)
- [基础信息](#基础信息)
- [系统接口](#系统接口)
- [文档索引接口](#文档索引接口)
- [检索接口](#检索接口)
- [文档管理接口](#文档管理接口)
- [错误处理](#错误处理)

---

## 快速开始

### 1. 启动 API 服务

```bash
# 方式一：使用 uvicorn 直接运行
python -m uvicorn src.api_server:app --reload --host 0.0.0.0 --port 8000

# 方式二：使用 Python 脚本
cd src
python api_server.py
```

### 2. 访问 API 文档

启动服务后，可以访问以下地址查看自动生成的交互式文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 3. 测试 API

```bash
# 健康检查
curl http://localhost:8000/health

# 运行测试脚本
python test_api.py
```

---

## 基础信息

**Base URL**: `http://localhost:8000`

**版本**: v0.2.0

**认证**: 当前版本不需要认证（生产环境建议添加 API Key）

**内容类型**: `application/json`

---

## 系统接口

### GET / - 根路径

获取 API 基本信息。

**请求示例**:
```bash
curl http://localhost:8000/
```

**响应示例**:
```json
{
  "name": "PageIndex + seekdb 混合 RAG API",
  "version": "0.2.0",
  "docs": "/docs",
  "health": "/health"
}
```

---

### GET /health - 健康检查

检查服务状态。

**请求示例**:
```bash
curl http://localhost:8000/health
```

**响应示例**:
```json
{
  "status": "healthy",
  "version": "0.2.0",
  "seekdb_mode": "server",
  "cache_enabled": true
}
```

**响应字段**:
- `status`: 服务状态（`healthy` / `unhealthy`）
- `version`: API 版本
- `seekdb_mode`: seekdb 运行模式（`server` / `embedded`）
- `cache_enabled`: 缓存是否启用

---

### GET /stats - 统计信息

获取系统统计数据。

**请求示例**:
```bash
curl http://localhost:8000/stats
```

**响应示例**:
```json
{
  "success": true,
  "stats": {
    "total_nodes": 120,
    "total_chunks": 450,
    "collections": ["tree_nodes", "content_chunks"]
  },
  "cache_enabled": true,
  "seekdb_mode": "server"
}
```

---

## 文档索引接口

### POST /index - 索引本地文档

索引本地 PDF 文档到 seekdb。

**请求体**:
```json
{
  "document_id": "sample_001",
  "pdf_path": "data/sample.pdf"
}
```

**请求示例**:
```bash
curl -X POST http://localhost:8000/index \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "sample_001",
    "pdf_path": "data/sample.pdf"
  }'
```

**响应示例**:
```json
{
  "success": true,
  "document_id": "sample_001",
  "total_nodes": 40,
  "total_chunks": 150,
  "total_pages": 30,
  "message": "Document indexed successfully"
}
```

**参数说明**:
- `document_id` (required): 文档唯一标识符
- `pdf_path` (required): PDF 文件路径（相对或绝对路径）

**注意**:
- 索引过程可能需要几分钟，取决于文档大小
- 文档 ID 必须唯一，重复索引会覆盖旧数据

---

### POST /index/upload - 上传并索引文档

通过文件上传方式索引 PDF 文档。

**请求示例**:
```bash
curl -X POST http://localhost:8000/index/upload \
  -F "document_id=sample_002" \
  -F "file=@/path/to/document.pdf"
```

**响应示例**:
```json
{
  "success": true,
  "document_id": "sample_002",
  "total_nodes": 35,
  "total_chunks": 120,
  "total_pages": 25,
  "message": "Document indexed successfully"
}
```

**参数说明**:
- `document_id` (required): 文档唯一标识符（form field）
- `file` (required): PDF 文件（multipart/form-data）

---

## 检索接口

### POST /search - 混合检索

执行混合检索查询。

**请求体**:
```json
{
  "query": "文档的主要主题是什么？",
  "document_id": "sample_001",
  "strategy": "hybrid",
  "top_k": 5,
  "tree_weight": 0.4,
  "vector_weight": 0.6
}
```

**请求示例**:
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "什么是LSM-Tree存储架构？",
    "strategy": "hybrid",
    "top_k": 5
  }'
```

**响应示例**:
```json
{
  "success": true,
  "query": "什么是LSM-Tree存储架构？",
  "strategy": "hybrid",
  "total_results": 5,
  "results": [
    {
      "score": 0.8756,
      "content": "LSM-Tree（Log-Structured Merge Tree）是一种...",
      "node_path": ["存储架构", "LSM-Tree设计"],
      "page_num": 5,
      "chunk_id": "chunk_001",
      "metadata": {
        "document_id": "sample_001",
        "node_id": "node_005"
      }
    }
  ]
}
```

**参数说明**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `query` | string | ✅ | - | 检索查询文本 |
| `document_id` | string | ❌ | null | 文档ID过滤（不指定则搜索所有文档） |
| `strategy` | string | ❌ | "hybrid" | 检索策略：`tree_only` / `vector_only` / `hybrid` |
| `top_k` | integer | ❌ | 5 | 返回结果数量（1-100） |
| `tree_weight` | float | ❌ | 0.4 | 树检索权重（0-1） |
| `vector_weight` | float | ❌ | 0.6 | 向量检索权重（0-1） |
| `tree_max_depth` | integer | ❌ | 3 | 树搜索最大深度（1-10） |

**检索策略说明**:
- **`tree_only`**: 仅使用树结构检索（基于章节层级推理）
- **`vector_only`**: 仅使用向量检索（语义相似度）
- **`hybrid`**: 混合检索（推荐，准确率最高）

**响应字段**:
- `score`: 相关性分数（0-1）
- `content`: 内容文本
- `node_path`: 章节路径（从根到叶子）
- `page_num`: 页码
- `chunk_id`: 内容块ID
- `metadata`: 元数据（包含 document_id, node_id 等）

---

## 文档管理接口

### GET /documents - 列出所有文档

获取所有已索引的文档列表。

**请求示例**:
```bash
curl http://localhost:8000/documents
```

**响应示例**:
```json
{
  "success": true,
  "total_documents": 3,
  "documents": [
    {
      "document_id": "sample_001",
      "total_nodes": 40,
      "total_chunks": 150,
      "title": "存储架构设计"
    },
    {
      "document_id": "sample_002",
      "total_nodes": 35,
      "total_chunks": 120,
      "title": "分布式系统原理"
    }
  ]
}
```

---

### DELETE /documents/{document_id} - 删除文档

删除指定文档的所有数据。

**请求示例**:
```bash
curl -X DELETE http://localhost:8000/documents/sample_001
```

**响应示例**:
```json
{
  "success": true,
  "document_id": "sample_001",
  "nodes_deleted": 40,
  "chunks_deleted": 150,
  "message": "Document deleted successfully"
}
```

**注意**:
- 删除操作不可逆
- 会删除该文档的所有节点和内容块

---

## 错误处理

### 错误响应格式

所有错误响应遵循统一格式：

```json
{
  "detail": "Error message here"
}
```

### HTTP 状态码

| 状态码 | 说明 | 场景 |
|--------|------|------|
| 200 | 成功 | 请求成功处理 |
| 400 | 请求错误 | 参数错误、文件格式错误 |
| 404 | 未找到 | 文件不存在、文档不存在 |
| 500 | 服务器错误 | 内部处理异常 |
| 503 | 服务不可用 | 健康检查失败 |

### 常见错误示例

**404 - PDF 文件未找到**:
```json
{
  "detail": "PDF file not found: data/sample.pdf"
}
```

**400 - 参数错误**:
```json
{
  "detail": "pdf_path is required"
}
```

**500 - 服务器错误**:
```json
{
  "detail": "Failed to initialize seekdb: Connection refused"
}
```

---

## 高级用法

### 1. 批量索引

```python
import requests

documents = [
    ("doc1", "data/file1.pdf"),
    ("doc2", "data/file2.pdf"),
    ("doc3", "data/file3.pdf")
]

for doc_id, pdf_path in documents:
    response = requests.post(
        "http://localhost:8000/index",
        json={"document_id": doc_id, "pdf_path": pdf_path}
    )
    print(f"{doc_id}: {response.json()}")
```

### 2. 检索策略对比

```python
import requests

query = "什么是分布式共识？"

for strategy in ["tree_only", "vector_only", "hybrid"]:
    response = requests.post(
        "http://localhost:8000/search",
        json={"query": query, "strategy": strategy, "top_k": 3}
    )
    result = response.json()
    print(f"\n{strategy}: {result['total_results']} results")
    for i, item in enumerate(result['results'], 1):
        print(f"  {i}. Score: {item['score']:.4f} - {item['content'][:50]}...")
```

### 3. 权重调优

```python
# 增加树检索权重（更注重文档结构）
response = requests.post(
    "http://localhost:8000/search",
    json={
        "query": "第三章的主要内容",
        "strategy": "hybrid",
        "tree_weight": 0.7,
        "vector_weight": 0.3
    }
)

# 增加向量检索权重（更注重语义相似度）
response = requests.post(
    "http://localhost:8000/search",
    json={
        "query": "如何优化性能？",
        "strategy": "hybrid",
        "tree_weight": 0.3,
        "vector_weight": 0.7
    }
)
```

---

## Python SDK 示例

```python
"""
简单的 Python 客户端封装
"""

import requests
from typing import List, Dict, Any

class RAGClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    def health(self) -> Dict:
        """健康检查"""
        return requests.get(f"{self.base_url}/health").json()

    def index_document(self, document_id: str, pdf_path: str) -> Dict:
        """索引文档"""
        return requests.post(
            f"{self.base_url}/index",
            json={"document_id": document_id, "pdf_path": pdf_path}
        ).json()

    def search(
        self,
        query: str,
        document_id: str = None,
        strategy: str = "hybrid",
        top_k: int = 5
    ) -> List[Dict]:
        """检索"""
        response = requests.post(
            f"{self.base_url}/search",
            json={
                "query": query,
                "document_id": document_id,
                "strategy": strategy,
                "top_k": top_k
            }
        )
        return response.json()["results"]

    def list_documents(self) -> List[Dict]:
        """列出文档"""
        response = requests.get(f"{self.base_url}/documents")
        return response.json()["documents"]

    def delete_document(self, document_id: str) -> Dict:
        """删除文档"""
        return requests.delete(
            f"{self.base_url}/documents/{document_id}"
        ).json()

# 使用示例
client = RAGClient()

# 索引
result = client.index_document("my_doc", "data/my.pdf")
print(f"Indexed: {result['total_nodes']} nodes")

# 检索
results = client.search("什么是RAG？", strategy="hybrid", top_k=3)
for i, item in enumerate(results, 1):
    print(f"{i}. {item['content'][:100]}...")

# 列出文档
docs = client.list_documents()
print(f"Total documents: {len(docs)}")
```

---

## 生产部署建议

### 1. 使用 Gunicorn + Uvicorn Workers

```bash
pip install gunicorn

gunicorn src.api_server:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 600
```

### 2. Docker 部署

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "src.api_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3. 安全建议

- 添加 API Key 认证
- 启用 HTTPS
- 限制 CORS 域名
- 添加请求速率限制
- 使用环境变量管理敏感配置

---

## 常见问题

**Q: 如何处理大文件上传？**
A: 调整 `uvicorn` 的 `--limit-max-requests` 参数或使用异步索引。

**Q: 检索速度慢怎么办？**
A: 启用缓存（`ENABLE_CACHE=true`）或使用 `vector_only` 策略。

**Q: 如何支持多文档联合检索？**
A: 不指定 `document_id` 参数即可搜索所有文档。

**Q: 支持哪些文件格式？**
A: 目前仅支持 PDF 格式。

---

**文档版本**: v0.2.0
**最后更新**: 2026-01-05
