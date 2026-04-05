# 数据库迁移指南：MySQL → PostgreSQL/PostGIS (Docker)

> **本文档面向前端队友**，帮助你在本地环境中完成数据库切换。  
> 完成本指南后，你的本地后端将使用 Docker 中的 PostgreSQL/PostGIS 数据库。

---

## 📋 前置条件

| 工具 | 最低版本 | 安装检查 |
|------|----------|----------|
| Docker Desktop | 4.x | `docker --version` |
| Docker Compose | 2.x（Docker Desktop 自带） | `docker compose version` |
| Git | 任意 | `git --version` |
| uv (Python 包管理) | 0.4+ | `uv --version` |

> **Windows 用户**：确保 Docker Desktop 已启动，且 WSL2 后端正常运行。  
> **Mac 用户**：确保 Docker Desktop 已启动。

---

## 🚀 一键换库步骤

### 1. 拉取最新代码

```bash
git pull origin main
```

### 2. 启动 PostgreSQL/PostGIS 容器

```bash
docker compose up -d
```

这会自动：
- 拉取 `postgis/postgis:16-3.4` 镜像（首次约 500MB）
- 创建 `campus_nav` 数据库和 `campus_user` 用户
- 启用 PostGIS 和 uuid-ossp 扩展
- 端口映射 `127.0.0.1:5432`

**验证容器运行状态：**

```bash
docker compose ps
```

应该看到 `tourism_postgres` 状态为 `running (healthy)`。

### 3. 安装新依赖

```bash
uv sync
```

这会自动：
- 移除 `pymysql`
- 安装 `psycopg`（PostgreSQL 驱动）

### 4. 确认 `.env` 配置

打开 `.env` 文件，确认 `DATABASE_URL` 已更新为：

```env
DATABASE_URL=postgresql+psycopg://campus_user:campus_pass@127.0.0.1:5432/campus_nav
```

> 如果你之前手动改过 `.env`，请手动更新这一行。

### 5. 启动后端验证

```bash
uv run uvicorn src.api:app --reload
```

后端启动时会自动建表。看到类似日志即表示成功：

```
✅ 数据库表检查完毕！
✅ 地图加载成功，包含 XXX 个景点
```

### 6. （可选）初始化向量库

如果你需要 RAG 功能：

```bash
uv run python tools/init_vector_db.py
```

---

## 🔍 常见问题

### Q: `docker compose up -d` 失败，提示端口 5432 被占用？

**A:** 你本地可能已有 PostgreSQL/MySQL 占用了端口。

```bash
# 查看占用端口的进程
netstat -ano | findstr :5432

# 或者修改 docker-compose.yml 中的端口映射
# 改为 "127.0.0.1:15432:5432"
# 然后 .env 中的 DATABASE_URL 也要对应改端口
```

### Q: 后端启动报 `connection refused`？

**A:** Docker 容器可能还没完全启动。等几秒后重试：

```bash
docker compose ps     # 确认 healthy
docker compose logs   # 查看容器日志
```

### Q: 我本地还有 MySQL 的旧数据怎么办？

**A:** 切换后是全新的空数据库。后端启动时会自动建表。  
如果需要旧数据，联系后端同学执行数据迁移脚本。

### Q: 如何彻底清理重来？

```bash
# 停止并删除容器和数据卷
docker compose down -v

# 重新启动
docker compose up -d
```

### Q: 如何查看数据库内容？

```bash
# 方式1：使用项目内置工具
uv run python tools/view_database.py

# 方式2：直接连接 PostgreSQL
docker exec -it tourism_postgres psql -U campus_user -d campus_nav

# 常用 psql 命令
\dt          -- 列出所有表
\d user      -- 查看表结构
SELECT * FROM "user" LIMIT 5;  -- 查询数据（注意: user 是保留字，需要双引号）
\q           -- 退出
```

---

## 📊 变更摘要

| 变更项 | 旧值 | 新值 |
|--------|------|------|
| 数据库 | MySQL 8.x（本地安装） | PostgreSQL 16 + PostGIS 3.4（Docker） |
| 驱动 | pymysql | psycopg |
| 连接串 | `mysql+pymysql://root:root@127.0.0.1:3306/campus_nav` | `postgresql+psycopg://campus_user:campus_pass@127.0.0.1:5432/campus_nav` |
| 部署方式 | 本地安装 MySQL | `docker compose up -d` |
| 容器名 | — | `tourism_postgres` |
| 数据卷 | — | `tourism_pgdata`（持久化） |

---

## 🛠️ Docker 常用命令速查

```bash
docker compose up -d        # 启动数据库
docker compose down          # 停止数据库（保留数据）
docker compose down -v       # 停止并清除所有数据
docker compose ps            # 查看容器状态
docker compose logs -f       # 实时查看日志
docker compose restart       # 重启容器
```

---

## ⏪ 回滚方案（如需切回 MySQL）

如果遇到严重问题需要临时切回 MySQL：

1. 安装 pymysql：`uv add pymysql`
2. 修改 `.env`：

   ```env
   DATABASE_URL=mysql+pymysql://root:root@127.0.0.1:3306/campus_nav
   ```

3. 重启后端即可。

> 注意：代码层已兼容 PostgreSQL，回滚仅作为应急手段。

---

*最后更新：2026-04*
