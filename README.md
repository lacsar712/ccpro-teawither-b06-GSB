# TeaWither-01 · 茶萎凋台账

Django 5 + PostgreSQL 服务端渲染应用：Templates + HTMX + 自定义 CSS，无 Vue/React SPA。

## 技术栈

- Django 5、PostgreSQL
- Session 登录
- HTMX（CDN）局部刷新列表
- Docker Compose：`web` + `db`

## 端口与数据库

| 服务 | 端口 |
|------|------|
| Web  | **4100** |
| Postgres | **5440**（容器内 5432） |

数据库账号：`teawither` / `teawither` / 库名 `teawither`

## 快速启动

```bash
cd TeaWither/TeaWither-01
docker compose up --build -d
```

浏览器打开：http://localhost:4100

演示账号：

- `admin` / `123456`（超级用户）
- `witherer` / `123456`（普通用户）

容器启动时会自动：`migrate` → `seed_data` → `collectstatic` → `gunicorn`

## 本地开发（可选）

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
# 确保本机 Postgres 监听 5440，或先 docker compose up -d db
set POSTGRES_HOST=localhost
set POSTGRES_PORT=5440
python manage.py migrate
python manage.py seed_data
python manage.py runserver 0.0.0.0:4100
```

## 业务模型

1. **Garden（茶园）**：`name`、`altitudeBand`、`notes`
2. **Trough（萎凋槽）**：归属茶园、`troughCode`、`cultivar`、`loadKg`、状态 `loading|withering|ready`；同一茶园内槽位编号唯一
3. **WitherBatch（萎凋批次）**：归属槽位、`startedAt`、`targetMoisture`、`actualMoisture`（可空）、`rollGrade`

**业务规则**：将槽位状态设为 `ready`（可下槽）时，若最新批次的 `actualMoisture` 为空或大于 40，抛出中文 `ValidationError`。

## 种子数据

```bash
python manage.py seed_data
```

幂等：已有茶园则只保证账号存在。亦可在环境变量 `TEAWITHER_AUTO_SEED=1` 时于 `post_migrate` 自动播种。

种子为非零样例：3 个茶园、6 条槽位（装叶中/萎凋中/可下槽各有多条）、6 个批次（含实测含水率为空的批次）。

## 列表筛选与首页对账

- 萎凋槽列表支持按**状态**筛选（`/troughs/?status=loading|withering|ready`，缺省为全部）。
- 萎凋批次列表支持按**茶园**筛选（`/batches/?garden=<id>`，缺省为全部）。
- 筛选表单同时走整页 GET 与 HTMX 局部刷新（`hx-push-url`），两种方式渲染的是视图中**同一个 queryset**，行集合必然相同；「刷新列表」按钮会带上当前 query string。

首页四项指标**不写死数字、不另写 SQL**，全部由 `apps/gardens/views.py` 的行集函数 `garden_rows() / trough_rows(status=) / batch_rows(garden_id=)` 取 `.count()`，列表视图也调用同一组函数。可用列表在无额外手工条件下复算：

| 首页指标 | 复算方式（数行数） |
|---|---|
| 茶园总数 | `/gardens/` 无筛全量行数 |
| 槽总数 | `/troughs/` 状态选「全部状态」的行数 |
| 批次总数 | `/batches/` 茶园选「全部茶园」的行数 |
| 可下槽数 | `/troughs/?status=ready` 状态子集行数 |

对账以**无筛全量列表**为准；首页数字不随列表筛选条件变化。

## 目录结构

```
TeaWither-01/
  manage.py
  requirements.txt
  Dockerfile
  entrypoint.sh
  docker-compose.yml
  config/           # 项目配置
  apps/gardens/     # 模型、视图、种子命令
  templates/        # Django 模板
  static/css/       # 自定义样式（茶绿色顶栏）
```
