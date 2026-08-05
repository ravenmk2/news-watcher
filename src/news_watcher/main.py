"""入口：装配组件并启动 FastAPI 服务。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from .api import router
from .config import load_config
from .logging import setup_logging
from .scheduler import SourceScheduler
from .sources import build_source
from .storage import Storage
from .targets import build_target


def create_app(config_path: str | None = None) -> FastAPI:
    setup_logging()
    config = load_config(config_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        storage = Storage(config.storage.dir)
        sources = {name: build_source(name, cfg) for name, cfg in config.sources.items()}
        targets = {
            name: build_target(name, cfg) for name, cfg in config.targets.items()
        }
        scheduler = SourceScheduler(
            sources, config.sources, storage, targets, config.rules
        )
        scheduler.start()
        logger.info(
            "news-watcher 已启动：{} 个来源，{} 个 target，{} 条规则",
            len(sources),
            len(targets),
            len(config.rules),
        )
        yield
        await scheduler.shutdown()
        storage.close()

    app = FastAPI(title="news-watcher", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run(
        "news_watcher.main:app",
        host="0.0.0.0",
        port=load_config().server.port,
    )


if __name__ == "__main__":
    main()
