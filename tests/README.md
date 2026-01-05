# 测试文档

PageIndex + seekdb RAG 系统的单元测试套件。

## 📋 测试文件

| 文件 | 测试内容 | 测试数量 |
|------|---------|---------|
| `test_embedding_manager.py` | Embedding 向量化功能 | 15+ |
| `test_seekdb_manager.py` | seekdb 数据库管理 | 20+ |
| `test_hybrid_search.py` | 混合检索引擎 | 20+ |
| `conftest.py` | 共享 fixtures 和配置 | - |

**总计**: 55+ 个单元测试

---

## 🚀 快速开始

### 1. 安装测试依赖

```bash
pip install -r requirements.txt
```

关键依赖：
- `pytest>=7.4.0` - 测试框架
- `pytest-cov>=4.1.0` - 代码覆盖率

### 2. 运行所有测试

```bash
# 运行所有测试
pytest

# 运行并显示详细输出
pytest -v

# 运行并生成覆盖率报告
pytest --cov=src --cov-report=html
```

### 3. 查看覆盖率报告

```bash
# 打开 HTML 覆盖率报告
open htmlcov/index.html
```

---

## 📊 测试分类

### 按标记分类

测试使用 pytest markers 进行分类：

```bash
# 只运行单元测试（快速）
pytest -m "unit"

# 只运行 embedding 测试
pytest -m "embedding"

# 只运行 seekdb 测试
pytest -m "seekdb"

# 只运行搜索测试
pytest -m "search"

# 跳过集成测试（需要外部服务）
pytest -m "not integration"
```

### 按文件分类

```bash
# 只运行 embedding 测试
pytest tests/test_embedding_manager.py

# 只运行 seekdb 测试
pytest tests/test_seekdb_manager.py

# 只运行搜索测试
pytest tests/test_hybrid_search.py
```

---

## 🧪 测试内容详解

### test_embedding_manager.py

测试 `EmbeddingManager` 类的功能：

**基础功能**:
- ✅ 初始化和配置
- ✅ 单文本 embedding
- ✅ 批量 embedding
- ✅ Embedding 一致性
- ✅ Embedding 维度验证

**边界情况**:
- ✅ 空文本处理
- ✅ None 值处理
- ✅ 超长文本处理
- ✅ 特殊字符处理
- ✅ 大批量处理（50+ 文本）

**错误处理**:
- ✅ API 错误处理
- ✅ 网络错误处理

**示例**:
```bash
# 运行 embedding 测试
pytest tests/test_embedding_manager.py -v

# 运行特定测试
pytest tests/test_embedding_manager.py::TestEmbeddingManager::test_embed_single_text
```

---

### test_seekdb_manager.py

测试 `SeekDBManager` 类的功能：

**初始化测试**:
- ✅ Embedded 模式初始化
- ✅ Server 模式初始化（需要 Docker）
- ✅ 无效模式处理

**Collection 操作**:
- ✅ 创建 collections
- ✅ 自定义维度配置

**节点操作**:
- ✅ 插入单个节点
- ✅ 插入多个节点
- ✅ 搜索节点
- ✅ 带过滤器搜索

**内容块操作**:
- ✅ 插入单个 chunk
- ✅ 插入多个 chunks
- ✅ 搜索 chunks

**文档级操作**:
- ✅ 删除文档
- ✅ 列出文档
- ✅ 获取统计信息

**数据模型**:
- ✅ NodeRecord 验证
- ✅ ChunkRecord 验证

**错误处理**:
- ✅ 长度不匹配错误
- ✅ 维度错误

**示例**:
```bash
# 运行 seekdb 测试
pytest tests/test_seekdb_manager.py -v

# 跳过需要 Docker 的测试
pytest tests/test_seekdb_manager.py -v -m "not integration"
```

---

### test_hybrid_search.py

测试 `HybridSearchEngine` 类的功能：

**配置测试**:
- ✅ TreeSearchConfig
- ✅ VectorSearchConfig
- ✅ HybridSearchConfig
- ✅ 权重配置

**初始化测试**:
- ✅ 基本初始化
- ✅ 带缓存初始化
- ✅ 自定义配置

**检索策略**:
- ✅ tree_only 策略
- ✅ vector_only 策略
- ✅ hybrid 策略
- ✅ 无效策略处理

**高级功能**:
- ✅ 文档 ID 过滤
- ✅ 自定义 top_k
- ✅ 自定义权重
- ✅ 缓存命中

**结果处理**:
- ✅ 空结果合并
- ✅ 分数组合

**示例**:
```bash
# 运行搜索测试
pytest tests/test_hybrid_search.py -v

# 测试特定策略
pytest tests/test_hybrid_search.py::TestHybridSearch::test_hybrid_search_hybrid_strategy
```

---

## 🔧 测试配置

### pytest.ini

项目根目录的 `pytest.ini` 文件配置了：

- 测试发现模式
- 输出选项
- 标记定义
- 日志格式
- 警告过滤

### conftest.py

`tests/conftest.py` 提供了共享的 fixtures：

**配置 Fixtures**:
- `test_config` - 测试配置
- `temp_dir` - 临时目录

**数据 Fixtures**:
- `sample_text` - 示例文本
- `sample_texts` - 示例文本列表
- `sample_node_data` - 示例节点数据
- `sample_chunk_data` - 示例块数据

**组件 Fixtures**:
- `embedding_manager` - EmbeddingManager 实例
- `seekdb_manager_embedded` - SeekDBManager 实例（Embedded 模式）

---

## 📈 覆盖率目标

| 模块 | 目标覆盖率 | 当前状态 |
|------|-----------|---------|
| `embedding_manager.py` | 80%+ | ✅ |
| `seekdb_manager.py` | 75%+ | ✅ |
| `hybrid_search.py` | 70%+ | ✅ |
| `document_indexer.py` | 60%+ | 🔄 待实现 |

**总体目标**: 70%+ 代码覆盖率

---

## 🎯 最佳实践

### 1. 测试命名

遵循清晰的命名约定：

```python
# 好的命名
def test_embed_single_text():
    """Test embedding a single text"""

# 避免
def test_1():
    """Test"""
```

### 2. 使用 Fixtures

复用测试资源：

```python
@pytest.fixture
def sample_data():
    return {"key": "value"}

def test_function(sample_data):
    assert sample_data["key"] == "value"
```

### 3. 参数化测试

测试多个输入：

```python
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6)
])
def test_double(input, expected):
    assert input * 2 == expected
```

### 4. Mock 外部依赖

隔离单元测试：

```python
from unittest.mock import Mock

def test_with_mock():
    mock_db = Mock()
    mock_db.query.return_value = []
    # Test logic
```

### 5. 跳过条件测试

```python
@pytest.mark.skipif(
    not_available,
    reason="Requires external service"
)
def test_external():
    pass
```

---

## 🐛 故障排除

### 问题 1: 导入错误

```bash
# 确保项目根目录在 PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 或在测试中
import sys
sys.path.insert(0, str(project_root))
```

### 问题 2: API 密钥未设置

```bash
# 设置环境变量
export API_KEY=your_api_key

# 或在 .env 文件中
API_KEY=your_api_key
```

### 问题 3: seekdb 连接失败

```bash
# 启动 seekdb Docker
docker-compose up -d

# 或跳过需要 Docker 的测试
pytest -m "not integration"
```

### 问题 4: 测试运行缓慢

```bash
# 只运行快速单元测试
pytest -m "unit"

# 跳过慢速测试
pytest -m "not slow"

# 并行运行（需要 pytest-xdist）
pytest -n auto
```

---

## 📝 添加新测试

### 1. 创建测试文件

```python
# tests/test_new_module.py
import pytest
from src.new_module import NewClass

class TestNewClass:
    def test_basic_functionality(self):
        obj = NewClass()
        assert obj.method() == expected_value
```

### 2. 添加 Fixture

```python
# tests/conftest.py
@pytest.fixture
def new_fixture():
    return {"data": "value"}
```

### 3. 运行新测试

```bash
pytest tests/test_new_module.py -v
```

---

## 🔄 持续集成

### GitHub Actions 示例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          pytest --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## 📚 相关文档

- [Pytest 文档](https://docs.pytest.org/)
- [Pytest-cov 文档](https://pytest-cov.readthedocs.io/)
- [项目 README](../README.md)
- [API 文档](../docs/api.md)

---

## 🆘 获取帮助

遇到测试问题？

- 查看 pytest 输出的详细错误信息
- 使用 `pytest -v -s` 显示打印输出
- 查看 [pytest 文档](https://docs.pytest.org/)
- 提交 Issue: https://github.com/boathell/pageindex-seekdb-rag/issues

---

**最后更新**: 2026-01-05
**测试框架**: pytest 7.4.0+
**覆盖率工具**: pytest-cov 4.1.0+
