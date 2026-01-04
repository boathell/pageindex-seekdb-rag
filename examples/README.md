# 示例脚本说明

本目录包含各种示例脚本，演示如何使用 PageIndex + pyseekdb 混合RAG系统。

## 📁 文件说明

### 1. test_cache.py

**功能**：测试 `CacheManager` 的基本功能

**内容**：
- 查询结果缓存的读写
- 文档树缓存的读写
- 缓存统计信息
- 缓存清理功能
- 禁用缓存的测试

**运行**：
```bash
python examples/test_cache.py
```

**无需配置**：
- 不需要 OpenAI API Key
- 自动创建测试数据目录
- 使用模拟数据测试

---

### 2. demo_hybrid_search_with_cache.py

**功能**：演示完整的混合检索流程（带缓存）

**内容**：
- 初始化所有组件（含缓存）
- 第一次检索（无缓存）
- 第二次检索（缓存命中）
- 缓存性能对比
- Embedding LRU 缓存统计

**运行**：
```bash
python examples/demo_hybrid_search_with_cache.py
```

**需要配置**：
- ✅ 需要在 `.env` 中配置 `OPENAI_API_KEY`
- ✅ 需要有索引过的文档数据（或接受示例中的错误提示）

---

## 🚀 快速开始

### 步骤 1：配置环境变量

```bash
# 复制配置文件
cp .env.example .env

# 编辑 .env，填入你的 OpenAI API Key
vim .env
```

### 步骤 2：运行缓存测试

```bash
# 测试缓存基本功能（无需API Key）
python examples/test_cache.py
```

预期输出：
```
==============================================================
测试 CacheManager 基本功能
==============================================================

[1] 测试查询缓存
--------------------------------------------------------------
第一次查询（应该未命中）...
  结果: None
  耗时: 2.34ms

保存查询结果到缓存...
✓ Cached query result: 什么是混合RAG系统？

第二次查询（应该命中）...
✓ Cache hit for query: 什么是混合RAG系统？
  结果: 命中
  耗时: 1.15ms
  返回条目数: 2

...
```

### 步骤 3：体验完整流程

```bash
# 运行混合检索演示（需要API Key）
python examples/demo_hybrid_search_with_cache.py
```

---

## 📊 性能对比

### 启用缓存 vs 禁用缓存

| 操作 | 无缓存 | 有缓存 | 提升 |
|------|--------|--------|------|
| 第一次查询 | 200-500ms | 200-500ms | - |
| 第二次相同查询 | 200-500ms | 1-5ms | **100x** |
| Embedding调用 | 每次都调用API | LRU缓存命中 | 节省成本 |
| 树结构解析 | 每次都解析 | 持久化缓存 | 节省计算 |

---

## 💡 使用建议

### 何时启用缓存？

✅ **推荐启用**：
- 开发调试阶段
- 交互式问答场景
- 批量评测实验
- 高频重复查询

❌ **可以禁用**：
- 一次性批量处理
- 每次查询都不同
- 磁盘空间受限

### 缓存配置

在 `.env` 中配置：

```bash
# 启用/禁用缓存
ENABLE_CACHE=true

# 缓存过期时间（秒）
CACHE_TTL=900  # 15分钟

# 缓存Collection名称
CACHE_COLLECTION=cache_data
```

### 清理缓存

```python
from src import CacheManager
import pyseekdb

client = pyseekdb.PersistentClient(path="./data/pyseekdb")
cache_manager = CacheManager(client)

# 清理所有缓存
cache_manager.clear_all_cache()

# 清理过期缓存
cache_manager.clear_expired_cache()
```

---

## 🔧 故障排查

### 问题 1：ModuleNotFoundError

**错误**：
```
ModuleNotFoundError: No module named 'src'
```

**解决**：
```bash
# 确保从项目根目录运行
cd /path/to/pageindex-seekdb-rag
python examples/test_cache.py
```

### 问题 2：OpenAI API Key 未配置

**错误**：
```
⚠️  请先配置 OPENAI_API_KEY
```

**解决**：
```bash
cp .env.example .env
# 编辑 .env，填入真实的 API Key
```

### 问题 3：缓存未命中

**现象**：
每次查询都显示 "Cache miss"

**排查**：
1. 检查 `ENABLE_CACHE` 是否为 `true`
2. 确认查询文本完全相同（包括空格、标点）
3. 检查缓存是否过期（TTL）

---

## 📚 相关文档

- [CACHE_DESIGN.md](../CACHE_DESIGN.md) - 缓存方案详细设计
- [architecture.md](../architecture.md) - 系统架构文档
- [README.md](../README.md) - 项目主文档

---

## 🙋 需要帮助？

如有问题，请提交 Issue 或参考文档。
