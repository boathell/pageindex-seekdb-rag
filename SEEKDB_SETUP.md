# seekdb 部署与配置指南

本文档详细介绍如何配置和使用 seekdb 数据库的两种部署模式。

## 🚀 部署模式

seekdb 支持两种部署模式：

### 1️⃣ Server 模式（推荐）

使用 Docker 部署独立的 seekdb 服务器，适合生产环境和多客户端场景。

**优点：**
- ✅ 性能更好，支持并发访问
- ✅ 数据持久化在独立存储
- ✅ 易于监控和管理
- ✅ 支持分布式部署

**缺点：**
- ❌ 需要 Docker 环境
- ❌ 部署稍复杂

### 2️⃣ Embedded 模式

应用内嵌入式数据库，数据存储在本地文件系统。

**优点：**
- ✅ 零部署，开箱即用
- ✅ 适合开发和测试
- ✅ 无需外部依赖

**缺点：**
- ❌ 性能相对较低
- ❌ 不支持多客户端并发
- ❌ 数据锁定在单个应用

---

## 📋 Server 模式部署（推荐）

### 方法 1：使用 Docker Compose

1. **启动 seekdb 服务**

```bash
# 在项目根目录执行
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f seekdb
```

2. **验证服务**

```bash
# 检查端口是否监听
netstat -an | grep 2881

# 或使用 docker 命令
docker ps | grep seekdb
```

3. **停止服务**

```bash
docker-compose down

# 删除数据卷（谨慎操作）
docker-compose down -v
```

### 方法 2：直接使用 Docker

```bash
docker run -d \
  --name seekdb \
  -p 2881:2881 \
  -p 2886:2886 \
  -v ./data/seekdb:/var/lib/oceanbase \
  oceanbase/seekdb:latest
```

### 配置环境变量（Server 模式）

在 `.env` 文件中设置：

```bash
# seekdb Server 模式配置
SEEKDB_MODE=server
SEEKDB_HOST=127.0.0.1
SEEKDB_PORT=2881
SEEKDB_USER=root
SEEKDB_PASSWORD=
SEEKDB_DATABASE=rag_system
```

### Python 代码示例

```python
from src.seekdb_manager import SeekDBManager

# 连接到 Docker 部署的 seekdb
manager = SeekDBManager(
    mode="server",
    host="127.0.0.1",
    port=2881,
    user="root",
    password="",
    database="rag_system"
)

# 初始化 collections
manager.initialize_collections()

print("Connected to seekdb server successfully!")
```

---

## 📁 Embedded 模式部署

### 配置环境变量（Embedded 模式）

在 `.env` 文件中设置：

```bash
# seekdb Embedded 模式配置
SEEKDB_MODE=embedded
SEEKDB_PERSIST_DIR=./data/pyseekdb
```

### Python 代码示例

```python
from src.seekdb_manager import SeekDBManager

# 使用嵌入式模式
manager = SeekDBManager(
    mode="embedded",
    persist_directory="./data/pyseekdb",
    database="rag_system"
)

# 初始化 collections
manager.initialize_collections()

print("Initialized embedded seekdb successfully!")
```

---

## 🔄 模式切换

只需修改 `.env` 文件中的 `SEEKDB_MODE` 参数：

```bash
# 切换到 Server 模式
SEEKDB_MODE=server

# 切换到 Embedded 模式
SEEKDB_MODE=embedded
```

**注意：** 两种模式的数据是独立的，切换模式后需要重新索引数据。

---

## 🔧 常见问题

### Q1: Docker 容器无法启动

**检查端口占用：**
```bash
lsof -i :2881
```

**查看容器日志：**
```bash
docker logs seekdb
```

### Q2: 连接超时

确保 seekdb 容器正在运行：
```bash
docker ps | grep seekdb
```

检查防火墙设置：
```bash
# 确保端口 2881 和 2886 未被防火墙阻止
```

### Q3: 数据迁移

**从 Embedded 迁移到 Server：**

目前需要重新索引数据。未来版本将提供数据导入/导出工具。

### Q4: 性能优化

**Server 模式调优：**
- 增加 Docker 容器的内存限制
- 调整 seekdb 配置参数
- 使用 SSD 存储卷

---

## 📊 性能对比

| 指标 | Embedded 模式 | Server 模式 |
|------|--------------|------------|
| 启动速度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 查询性能 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 并发支持 | ⭐ | ⭐⭐⭐⭐⭐ |
| 部署难度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 生产就绪 | ❌ | ✅ |

---

## 📚 参考资源

- [seekdb 官方文档](https://www.oceanbase.ai/docs/deploy-seekdb-testing-environment/)
- [seekdb GitHub](https://github.com/oceanbase/seekdb)
- [Docker Hub - seekdb](https://hub.docker.com/r/oceanbase/seekdb)

---

## 🆘 获取帮助

遇到问题？

1. 查看 [GitHub Issues](https://github.com/oceanbase/seekdb/issues)
2. 阅读 [官方文档](https://www.oceanbase.ai/)
3. 提交 Issue 到本项目
