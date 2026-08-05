"""print target：只打印日志。"""

from loguru import logger

from news_watcher.models import NewsItem
from news_watcher.targets.print import PrintTarget


def items() -> list[NewsItem]:
    return [
        NewsItem(id="1", title="标题一", url="https://a.com/1", content="内容一"),
        NewsItem(id="2", title="标题二", url="https://a.com/2", content="内容二"),
    ]


async def test_print_target_logs_each_item():
    records = []
    sink_id = logger.add(records.append, level=0, format="{level}:{message}")
    try:
        await PrintTarget("console").send(items())
    finally:
        logger.remove(sink_id)
    assert len(records) == 2
    assert "标题一" in records[0] and "https://a.com/1" in records[0]
    assert "[target:console]" in records[0]


async def test_print_target_respects_level():
    records = []
    sink_id = logger.add(records.append, level=0, format="{level}:{message}")
    try:
        await PrintTarget("console", level="warning").send(items())
    finally:
        logger.remove(sink_id)
    assert all(r.startswith("WARNING:") for r in records)
