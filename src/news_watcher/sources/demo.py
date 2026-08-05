"""示例来源：生成确定性的演示条目，用于验证流程与联调通知。"""

import time
from typing import Any

from ..models import NewsItem
from . import register_source
from .base import FetchResult, NewsSource


@register_source("demo")
class DemoSource(NewsSource):
    """每分钟生成一批新条目（id 按分钟变化），便于观察首抓忽略与增量通知。

    不支持状态过滤：忽略 state 返回全量，由 pipeline 做 DB 比对。
    """

    def __init__(self, name: str, batch_size: int = 3, **params):
        super().__init__(name, **params)
        self.batch_size = int(batch_size)

    async def fetch(self, state: dict[str, Any]) -> FetchResult:
        batch = int(time.time() // 60)
        items = [
            NewsItem(
                id=f"demo-{batch}-{i}",
                title=f"演示新闻 {batch}-{i}",
                url=f"https://example.com/news/{batch}/{i}",
                content=f"这是来源 {self.name} 在第 {batch} 批生成的第 {i} 条演示内容。",
                source=self.name,
            )
            for i in range(self.batch_size)
        ]
        return FetchResult(items=items, state=state)
