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

## 列表筛选

- 槽列表 `/troughs/`：`?status=loading|withering|ready` 按状态筛，`全部状态`（无参数）为全量。
- 批次列表 `/batches/`：`?garden=<茶园id>` 按茶园筛，`全部茶园`（无参数）为全量。
- 非法/未知参数一律按无筛全量处理；筛选下拉变更即 HTMX 局部刷新表格（无 JS 时表单整页提交同样生效），地址栏同步 querystring，刷新/分享链接结果一致。

## 首页四项对账

首页统计与三个列表共用同一组 queryset 构造函数（`apps/gardens/views.py` 的
`garden_list_queryset()` / `trough_list_queryset()` / `batch_list_queryset()`），
筛选只在其上追加条件，不存在首页另写 SQL 的第二口径。改筛条件不影响首页数字；
对账一律以**无筛全量列表**为准：

| 首页数字 | 复算方法 |
|----------|----------|
| 茶园总数 | 打开茶园列表 `/gardens/`，数表格行数 |
| 槽总数 | 打开槽列表 `/troughs/`，状态选「全部状态」，数表格行数 |
| 批次总数 | 打开批次列表 `/batches/`，茶园选「全部茶园」，数表格行数 |
| 可下槽数 | 打开槽列表 `/troughs/?status=ready`（状态选「可下槽」），数该状态子集行数 |

首页六张卡片均可点击直达对应列表（三个状态卡自带 `?status=...`），点过去数行即可复算。
HTMX 局部刷新与整页打开走同一个 `get_queryset()`，同参数下两者行集合必然相同；
`seed_data` 后四项均非零，且每个状态子集、每个茶园的批次子集都非空，可直接演练筛选与对账。

## 种子数据

```bash
python manage.py seed_data
```

幂等：已有茶园则只保证账号存在。亦可在环境变量 `TEAWITHER_AUTO_SEED=1` 时于 `post_migrate` 自动播种。

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
