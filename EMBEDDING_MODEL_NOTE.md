# Embedding 模型选择说明

## ⚠️ text-embedding-async-v2 不适用

经测试发现，**text-embedding-async-v2** 模型**不支持 OpenAI 兼容模式**的实时调用。

### 错误信息
```
Error code: 404 - Unsupported model `text-embedding-async-v2` for OpenAI compatibility mode.
```

### text-embedding-async-v2 的实际用途

这是一个**批处理异步模型**，使用方式为：
1. 上传文本文件到 OSS（每行一个文本）
2. 调用异步 API 处理整个文件
3. 等待处理完成
4. 下载 .gz 压缩结果文件

### 适用场景对比

| 模型 | 调用模式 | 适用场景 | 本项目是否可用 |
|------|---------|---------|---------------|
| text-embedding-v2 | 同步实时 | 在线文档索引、实时检索 | ✅ 可用 |
| text-embedding-async-v2 | 批处理异步 | 离线大规模文本处理 | ❌ 不可用 |

## ✅ 推荐配置

### 使用 text-embedding-v2（当前配置）

```bash
# .env 文件
OPENAI_EMBEDDING_MODEL=text-embedding-v2
```

**特点**：
- ✅ 支持 OpenAI 兼容模式
- ✅ 实时调用，适合在线索引
- ⚠️ 批量限制：25 个文本/请求
- 自动分批处理已实现

### 备选方案

如果需要更高性能，可以考虑：
- **OpenAI text-embedding-3-small**：2048 个文本/请求
- **OpenAI text-embedding-3-large**：3072 维，最高精度

## 📊 版本历史

- **v0.2.1** (2026-01-04): 误推荐 text-embedding-async-v2 → 已回退
- **v0.2.0** (2026-01-04): 使用 text-embedding-v2（正确配置）

---

**最后更新**: 2026-01-05
