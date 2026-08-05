# news-watcher

资讯观察和投递服务：按 cron 定时抓取多种新闻来源，发现新条目后按规则投递到多个目标 target（当前支持钉钉机器人、print 日志）。

## 功能

- **多新闻来源**：每种来源一个抓取组件，统一抽象（`NewsSource`），可插拔扩展；每条新闻包含 id、title、url、content 并入库。内置 `demo`（示例源）与 `deepseek_update`（DeepSeek API 更新日志）。
- **抓取状态**：来源可声明支持状态过滤（`supports_state`），利用持久化的状态只返回新条目；不支持的来源由服务侧与数据库比对去重。
- **多投递目标**：target 不一定是直接发通知（可以是机器人推送、日志打印、回调等）。每种类型可配置多个实例，统一抽象（`Target`），已实现钉钉机器人（支持加签）与 print（只打印日志）。
- **规则**：命名规则 `[rules.<rule_name>]` 绑定一种来源 + 多个 target；来源产生新条目时向全部 target 投递，单个 target 失败互不影响。
- **首抓忽略**：来源首次抓取的条目全部入库作为基线，不触发投递。

## 技术栈

Python ≥ 3.14 · uv · FastAPI · APScheduler · SQLite · loguru · httpx · BeautifulSoup

## 快速开始

```bash
# 安装依赖
uv sync

# 准备配置
cp config.example.toml config.toml
# 编辑 config.toml：填入钉钉 access_token 等

# 运行测试
uv run pytest

# 启动服务
uv run news-watcher
# 或
uv run uvicorn news_watcher.main:app --port 8000
```

## 配置说明（config.toml）

```toml
[server]
port = 8000                 # 服务端口，环境变量 NEWS_WATCHER_PORT 可覆盖

[storage]
dir = "data"                # 数据目录，数据库固定为 <dir>/news_watcher.db

[sources.deepseek]          # 每个 [sources.<name>] 是一种来源实例
type = "deepseek_update"    # 来源类型（注册表中的 type 名）
cron = "13 9 * * *"         # 抓取时机，5 段式 cron

[targets.console]            # 每个 [targets.<name>] 是一个 target
type = "print"              # print：只打印日志，可选 level
# type = "dingtalk"         # dingtalk：必填 access_token，可选 secret（加签）

[rules.deepseek_updates]    # 命名规则（英文标识符）：来源 → 多个 target
source = "deepseek"
targets = ["console"]
```

配置文件路径默认 `./config.toml`，可用环境变量 `NEWS_WATCHER_CONFIG` 指定。

## Docker 部署

```bash
docker build -t news-watcher .

docker run -d --name news-watcher \
  -p 8000:8000 \
  -v $(pwd)/config.toml:/app/config/config.toml:ro \
  -v news-watcher-data:/app/data \
  news-watcher
```

镜像为多阶段构建：构建阶段用 uv 创建虚拟环境安装依赖（包源为阿里云镜像，见 `pyproject.toml`），运行阶段仅拷贝 `.venv`，以非 root 用户运行。SQLite 数据存于 `/app/data`（建议挂卷），配置挂载到 `/app/config/config.toml`。

## API

当前仅提供 `GET /health` 健康检查，后续按需扩展。

## 扩展

新增来源或 target 类型只需新增一个文件并实现抽象接口，详见 [AGENTS.md](AGENTS.md)。
