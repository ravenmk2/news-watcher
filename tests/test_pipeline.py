"""pipeline：首抓忽略、增量通知、规则分发、状态机制、异常隔离。"""

import pytest

from news_watcher.config import RuleConfig
from news_watcher.models import NewsItem
from news_watcher.targets.base import Target
from news_watcher.pipeline import run_source, run_source_safe
from news_watcher.sources.base import FetchResult, NewsSource
from news_watcher.storage import Storage


class FakeSource(NewsSource):
    """不支持状态的来源：返回全量，由 pipeline 比对。"""

    def __init__(self, name, batches):
        super().__init__(name)
        self._batches = list(batches)

    async def fetch(self, state):
        return FetchResult(self._batches.pop(0) if self._batches else [], state)


class StatefulSource(NewsSource):
    """支持状态的来源：利用状态只返回新条目。"""

    supports_state = True

    def __init__(self, name, all_items):
        super().__init__(name)
        self._all = all_items
        self.received_states = []

    async def fetch(self, state):
        self.received_states.append(dict(state))
        seen = set(state.get("seen", []))
        new = [it for it in self._all if it.id not in seen]
        return FetchResult(new, {"seen": [it.id for it in self._all]})


class FakeTarget(Target):
    def __init__(self, name, fail=False):
        super().__init__(name)
        self.received: list[list[NewsItem]] = []
        self.fail = fail

    async def send(self, items):
        if self.fail:
            raise RuntimeError("boom")
        self.received.append(items)


def item(news_id: str) -> NewsItem:
    return NewsItem(id=news_id, title="t", url="u", content="c")


@pytest.fixture
def storage():
    s = Storage(":memory:")
    yield s
    s.close()


async def test_first_fetch_is_baseline_without_notify(storage):
    source = FakeSource("s1", [[item("a"), item("b")]])
    target = FakeTarget("n1")
    rules = {"r1": RuleConfig(source="s1", targets=["n1"])}

    new = await run_source(source, storage, {"n1": target}, rules)

    assert new == []
    assert target.received == []
    assert storage.is_initialized("s1")
    assert storage.filter_new("s1", [item("a"), item("b")]) == []


async def test_second_fetch_notifies_only_new_items(storage):
    source = FakeSource("s1", [[item("a")], [item("a"), item("b")]])
    target = FakeTarget("n1")
    rules = {"r1": RuleConfig(source="s1", targets=["n1"])}

    await run_source(source, storage, {"n1": target}, rules)
    new = await run_source(source, storage, {"n1": target}, rules)

    assert [it.id for it in new] == ["b"]
    assert len(target.received) == 1
    assert [it.id for it in target.received[0]] == ["b"]


async def test_multiple_targets_and_failure_isolation(storage):
    source = FakeSource("s1", [[], [item("a")]])
    ok, bad = FakeTarget("n1"), FakeTarget("n2", fail=True)
    rules = {"r1": RuleConfig(source="s1", targets=["n1", "n2"])}

    await run_source(source, storage, {"n1": ok, "n2": bad}, rules)
    new = await run_source(source, storage, {"n1": ok, "n2": bad}, rules)

    assert [it.id for it in new] == ["a"]
    assert len(ok.received) == 1  # n2 失败不影响 n1


async def test_stateful_source_skips_db_compare_and_persists_state(storage):
    source = StatefulSource("s1", [item("a")])
    target = FakeTarget("n1")
    rules = {"r1": RuleConfig(source="s1", targets=["n1"])}

    await run_source(source, storage, {"n1": target}, rules)
    assert storage.get_state("s1") == {"seen": ["a"]}

    # 来源收到的 state 是持久化的状态；返回的新条目直接可信（不经 DB 比对）
    await run_source(source, storage, {"n1": target}, rules)
    assert source.received_states[1] == {"seen": ["a"]}
    assert len(target.received) == 0


async def test_stateful_source_reports_new_items(storage):
    source = StatefulSource("s1", [item("a")])
    target = FakeTarget("n1")
    rules = {"r1": RuleConfig(source="s1", targets=["n1"])}
    await run_source(source, storage, {"n1": target}, rules)

    source._all.append(item("b"))
    new = await run_source(source, storage, {"n1": target}, rules)

    assert [it.id for it in new] == ["b"]
    assert storage.get_state("s1") == {"seen": ["a", "b"]}


async def test_run_source_safe_swallows_fetch_errors(storage):
    class BrokenSource(NewsSource):
        async def fetch(self, state):
            raise RuntimeError("network down")

    result = await run_source_safe(BrokenSource("s1"), storage, {}, {})
    assert result == []
