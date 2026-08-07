# AGENTS.md

## 项目概览

news-watcher：资讯观察和投递服务。按 cron 抓取多来源新闻（FastAPI + APScheduler），新条目入库（SQLite）并按命名规则投递到多个 target（钉钉机器人、print 日志）。日志统一使用 loguru。Python ≥ 3.14，uv 管理依赖，包源锁定为阿里云镜像（`pyproject.toml` 的 `[[tool.uv.index]]`）。

## 目录结构

```
src/news_watcher/
├── main.py            # 入口：装配组件 + FastAPI lifespan 启停调度器；`uv run news-watcher`
├── config.py          # TOML 配置加载（tomllib）+ pydantic 校验；NEWS_WATCHER_CONFIG / NEWS_WATCHER_PORT 环境变量
├── models.py          # NewsItem(id, title, url, content, source)
├── storage.py         # SQLite：news 表（代理主键 + UNIQUE(source, news_id)）、source_state（首抓标记 + 抓取状态 JSON）
├── pipeline.py        # 核心流程：抓取 → 去重（首抓忽略）→ 按规则分发到各 target；run_source_safe 供调度器调用（异常隔离）
├── scheduler.py       # SourceScheduler：每个来源一条 cron job（CronTrigger.from_crontab）
├── api.py             # FastAPI 路由（当前仅 /health）
├── logging.py         # loguru 初始化，拦截 uvicorn/apscheduler 标准日志
├── sources/           # 来源组件：base.py 抽象 + 注册表工厂（__init__.py）+ demo.py / deepseek.py / zhipu.py
└── targets/            # target 组件：base.py 抽象 + 注册表工厂（__init__.py）+ dingtalk.py / print.py
tests/                 # pytest，asyncio_mode = "auto"
```

## 架构约定

- **注册表 + 工厂**：`NewsSource`/`Target` 子类用 `@register_source("type")` / `@register_target("type")` 注册，工厂按配置 `type` 实例化。配置中 `type` 之外的字段作为 `**params` 传入构造函数。
- **NewsItem.id 在来源内唯一**，由来源组件保证；存储层用 `UNIQUE(source, news_id)` 去重。
- **抓取状态**：`fetch(state) -> FetchResult(items, state)`，状态由存储层按来源持久化（`source_state.state`，JSON）。`supports_state = True` 的来源须用状态只返回新条目（pipeline 不再比对）；否则忽略状态返回全量，由 pipeline 做 DB 比对。
- **首抓忽略**：`source_state.initialized` 为假时，抓到的条目全部入库作基线、不投递（pipeline 中实现，不要在来源组件里处理）。
- **异常隔离**：单来源抓取失败、单 target 投递失败都只记日志，不影响其他来源/target（`run_source_safe` + `asyncio.gather(return_exceptions=True)`）。
- 数据库不用复合主键：`news` 表用自增代理主键 + 唯一索引；存储配置只给目录（`[storage] dir`），库名固定 `news_watcher.db`。
- 规则为命名表 `[rules.<rule_name>]`（英文标识符），`AppConfig.rules: dict[str, RuleConfig]`；`sources`/`targets` 均为列表，一条规则可匹配多个来源。
- 新增代码走异步（httpx），存储层 sqlite3 同步调用可接受（毫秒级）。

## 新增一种来源

1. 在 `src/news_watcher/sources/` 新建 `<name>.py`，继承 `NewsSource`，实现 `async def fetch(self, state) -> FetchResult`。
2. 类上加 `@register_source("type_name")`；若来源支持状态过滤，设 `supports_state = True` 并在 state 中记录已见标识。
3. 在 `src/news_watcher/sources/__init__.py` 末尾导入该模块（触发注册）。
4. 配置 `[sources.<name>] type = "type_name"` + `cron` + 组件参数。

## 新增一种 target 类型

1. 在 `src/news_watcher/targets/` 新建 `<name>.py`，继承 `Target`，实现 `async def send(self, items: list[NewsItem]) -> None`。
2. 类上加 `@register_target("type_name")`。
3. 在 `src/news_watcher/targets/__init__.py` 末尾导入该模块。
4. 配置 `[targets.<name>] type = "type_name"` + 组件参数，并在 `[rules.<rule_name>]` 的 `targets` 中引用。

## 常用命令

```bash
uv sync                       # 安装依赖
uv run pytest                 # 跑测试
uv run news-watcher           # 启动服务（读 ./config.toml）
docker build -t news-watcher .  # 构建镜像
```
