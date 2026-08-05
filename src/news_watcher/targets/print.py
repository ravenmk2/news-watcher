"""print target：只打印日志，用于调试与本地观察。"""

from loguru import logger

from ..models import NewsItem
from . import register_target
from .base import Target


@register_target("print")
class PrintTarget(Target):
    def __init__(self, name: str, level: str = "INFO", **params):
        super().__init__(name, **params)
        self.level = level.upper()

    async def send(self, items: list[NewsItem]) -> None:
        for it in items:
            logger.log(
                self.level,
                "[target:{}] {} | {} | {}",
                self.name,
                it.title,
                it.url,
                it.content[:100],
            )
