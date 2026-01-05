# Jupyter Notebooks

本目录包含用于演示和评测 PageIndex + seekdb RAG 系统的交互式笔记本。

## 📚 笔记本列表

### 1. demo.ipynb - 系统完整演示 ⭐

**内容**:
- 系统初始化和配置
- 文档索引演示（PageIndex + seekdb）
- 三种检索策略对比（tree_only / vector_only / hybrid）
- 结果可视化和分析
- 权重调优演示
- 多查询测试
- 系统统计

**适合人群**: 初次使用者、需要了解系统功能的用户

**预计时间**: 15-20 分钟

---

## 🚀 快速开始

### 1. 安装依赖

确保已安装所有必要的依赖：

```bash
pip install -r requirements.txt
```

关键依赖包括：
- `jupyter` - Jupyter 笔记本
- `matplotlib` - 可视化
- `seaborn` - 统计图表
- `pandas` - 数据处理

### 2. 启动 Jupyter

```bash
# 启动 Jupyter Notebook
jupyter notebook

# 或使用 JupyterLab (推荐)
jupyter lab
```

### 3. 打开笔记本

在浏览器中导航到 `notebooks/demo.ipynb` 并运行单元格。

---

## ⚙️ 环境准备

在运行笔记本之前，请确保：

### 1. seekdb 正在运行

```bash
# 检查 seekdb 状态
docker ps | grep seekdb

# 如果未运行，启动它
docker-compose up -d
```

### 2. 配置 API Key

确保 `.env` 文件已正确配置：

```bash
# 复制示例配置
cp .env.example .env

# 编辑并填入你的 API Key
vim .env
```

需要配置：
- `API_KEY` 或 `OPENAI_API_KEY`
- `MODEL_NAME` (如 qwen-max 或 gpt-4)
- `OPENAI_EMBEDDING_MODEL` (如 text-embedding-v2)

### 3. 准备测试 PDF

确保有测试 PDF 文件：

```bash
# 示例文件
data/1282-1311_存储架构.pdf
```

---

## 📖 使用指南

### demo.ipynb 使用流程

1. **按顺序执行单元格**
   - 从顶部开始，逐个运行单元格（Shift + Enter）
   - 或使用 "Run All" 运行所有单元格

2. **关键步骤**
   - **环境设置**: 导入库和配置
   - **系统检查**: 验证 seekdb 状态
   - **文档索引**: 索引 PDF（约 2-5 分钟）
   - **检索测试**: 执行查询并查看结果
   - **可视化**: 查看对比图表

3. **自定义配置**
   - 修改 `query` 变量来测试不同查询
   - 调整 `top_k` 参数改变返回结果数
   - 修改权重配置测试不同效果

### 常见操作

```python
# 修改查询
query = "你的问题"

# 调整返回数量
top_k = 10

# 切换检索策略
strategy = "hybrid"  # 或 "tree_only", "vector_only"

# 自定义权重
config = HybridSearchConfig(
    tree_weight=0.6,
    vector_weight=0.4
)
```

---

## 🎨 可视化说明

### 1. 策略对比图

展示三种检索策略的平均分数：
- 柱状图对比各策略效果
- 折线图显示 Top-5 分数趋势

### 2. 权重影响图

展示不同权重配置的效果：
- 平均分数对比
- Top-1 结果分数对比

### 3. 数据表格

- 检索结果详情表
- 统计摘要表
- 多查询测试结果表

---

## 🔧 故障排除

### 问题 1: Jupyter 无法启动

```bash
# 重新安装 Jupyter
pip install --upgrade jupyter notebook
```

### 问题 2: 导入错误

```bash
# 确保在项目根目录
cd /path/to/pageindex-seekdb-rag

# 重新安装依赖
pip install -r requirements.txt
```

### 问题 3: seekdb 连接失败

```bash
# 检查 seekdb 是否运行
docker ps | grep seekdb

# 重启 seekdb
docker-compose restart seekdb

# 查看日志
docker-compose logs seekdb
```

### 问题 4: PageIndex 解析失败

- 检查 API Key 是否正确
- 确保 PDF 文件存在
- 查看 `external/PageIndex` 是否已克隆

### 问题 5: 可视化不显示

```bash
# 安装可视化库
pip install matplotlib seaborn

# 在 Jupyter 中启用内联显示
%matplotlib inline
```

---

## 💡 高级用法

### 1. 修改为使用自己的文档

```python
# 在 "文档索引演示" 单元格中修改
pdf_path = project_root / "data" / "your_document.pdf"
document_id = "your_doc_id"
```

### 2. 批量测试多个文档

```python
documents = [
    ("doc1", "data/file1.pdf"),
    ("doc2", "data/file2.pdf")
]

for doc_id, pdf in documents:
    result = document_indexer.index_document(
        pdf_path=pdf,
        document_id=doc_id
    )
    print(f"Indexed {doc_id}: {result['total_nodes']} nodes")
```

### 3. 导出结果

```python
# 保存结果到 CSV
df.to_csv('search_results.csv', index=False)

# 保存图表
fig.savefig('comparison.png', dpi=300, bbox_inches='tight')
```

### 4. 集成到工作流

```python
# 自动化检索流程
def auto_search(queries):
    all_results = []
    for q in queries:
        results = search_engine.hybrid_search(
            query=q,
            strategy="hybrid",
            top_k=5
        )
        all_results.append({
            'query': q,
            'top_score': results[0].score if results else 0,
            'result_count': len(results)
        })
    return pd.DataFrame(all_results)

# 使用
test_queries = ["查询1", "查询2", "查询3"]
results_df = auto_search(test_queries)
```

---

## 📊 性能提示

### 1. 加速索引

- 使用更快的 embedding 模型
- 减小 `chunk_size` 参数
- 启用缓存（`ENABLE_CACHE=true`）

### 2. 优化检索速度

- 使用 `vector_only` 策略（最快）
- 减小 `top_k` 值
- 限制搜索范围（指定 `document_id`）

### 3. 内存优化

- 分批处理大文档
- 定期清理缓存
- 使用 `del` 释放大对象

---

## 🎓 学习路径

### 初学者
1. 运行 `demo.ipynb` 完整流程
2. 理解三种检索策略的差异
3. 尝试修改查询测试效果

### 中级用户
1. 自定义权重配置
2. 测试不同类型的查询
3. 分析可视化结果

### 高级用户
1. 批量处理多个文档
2. 集成到自己的工作流
3. 开发自定义评测脚本

---

## 📚 相关文档

- [README.md](../README.md) - 项目概览
- [API 文档](../docs/api.md) - RESTful API 使用
- [部署指南](../DEPLOYMENT.md) - 生产环境部署

---

## 🆘 获取帮助

遇到问题？

- 查看 [DEPLOYMENT.md](../DEPLOYMENT.md) 的常见问题部分
- 提交 Issue: https://github.com/boathell/pageindex-seekdb-rag/issues
- 查看项目 README: [README.md](../README.md)

---

**最后更新**: 2026-01-05
**笔记本版本**: v1.0
