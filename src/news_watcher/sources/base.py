"""新闻来源抽象。"""

from abc import ABC, abstractmethod
from typing import Any, ClassVar, NamedTuple

from ..models import NewsItem


class FetchResult(NamedTuple):
    items: list[NewsItem]
    state: dict[str, Any]  # 更新后的状态（无变化可原样返回）


class NewsSource(ABC):
    """一种新闻来源的抓取组件。

    子类实现 `fetch()` 返回条目与更新后的状态；每条 `NewsItem.id` 必须在本来源内唯一。
    通过 `@register_source("类型名")` 注册后，可在配置中以 `type = "类型名"` 引用。

    状态机制：pipeline 每次 fetch 传入上次持久化的状态（首次为 {}），结束后持久化
    返回的新状态。`supports_state = True` 的来源应利用状态只返回新条目（pipeline
    不再做 DB 比对）；不支持的来源忽略状态返回全量，由 pipeline 比对去重。
    """

    supports_state: ClassVar[bool] = False

    def __init__(self, name: str, **params):
        self.name = name

    @abstractmethod
    async def fetch(self, state: dict[str, Any]) -> FetchResult:
        """抓取条目。state 为上次持久化的状态（首次为 {}）。"""
