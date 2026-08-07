"""demo 来源：基本行为与注册。"""

from news_watcher.sources import available_types, build_source
from news_watcher.config import SourceConfig
from news_watcher.sources.demo import DemoSource


async def test_demo_fetch_returns_items():
    source = DemoSource("demo", batch_size=2)
    result = await source.fetch({})
    assert len(result.items) == 2
    assert all(it.source == "demo" for it in result.items)
    assert len({it.id for it in result.items}) == 2
    assert result.state == {}


def test_source_registry():
    assert set(available_types()) == {"demo", "deepseek_update", "zhipu_release"}
    source = build_source("demo", SourceConfig(type="demo", cron="* * * * *"))
    assert isinstance(source, DemoSource)
