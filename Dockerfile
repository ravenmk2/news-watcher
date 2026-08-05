# syntax=docker/dockerfile:1

# ---- 构建阶段：用 uv 在虚拟环境中安装依赖 ----
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# 先拷贝依赖清单，利用构建缓存
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 再拷贝源码并安装项目本身
COPY src ./src
RUN uv sync --frozen --no-dev

# ---- 运行阶段：仅拷贝虚拟环境与必要文件 ----
FROM python:3.14-slim-bookworm

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH" \
    NEWS_WATCHER_CONFIG=/app/config/config.toml

RUN groupadd --system app && useradd --system --gid app app \
    && mkdir -p /app/data /app/config && chown -R app:app /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/src /app/src

USER app
VOLUME ["/app/data"]

EXPOSE 8000

CMD ["python", "-m", "news_watcher.main"]
