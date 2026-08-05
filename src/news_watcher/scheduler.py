"""APScheduler 封装：按各来源的 cron 表达式注册抓取任务。"""

from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from .config import SourceConfig
from .pipeline import run_source_safe
from .sources.base import NewsSource
from .storage import Storage
from .targets.base import Target


class SourceScheduler:
    def __init__(
        self,
        sources: dict[str, NewsSource],
        source_configs: dict[str, SourceConfig],
        storage: Storage,
        targets: dict[str, Target],
        rules: dict,
    ):
        self._scheduler = AsyncIOScheduler()
        self._sources = sources
        self._source_configs = source_configs
        self._storage = storage
        self._targets = targets
        self._rules = rules

    def start(self) -> None:
        for name, source in self._sources.items():
            cfg = self._source_configs[name]
            self._scheduler.add_job(
                run_source_safe,
                trigger=CronTrigger.from_crontab(cfg.cron),
                args=(source, self._storage, self._targets, self._rules),
                id=f"source:{name}",
                name=f"抓取来源 {name}",
                max_instances=1,
            )
            logger.info("已注册来源 {} 的抓取任务，cron: {}", name, cfg.cron)
        self._scheduler.start()

    async def shutdown(self) -> None:
        self._scheduler.shutdown(wait=False)
