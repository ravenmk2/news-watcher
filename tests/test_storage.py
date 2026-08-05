"""存储层：首抓标记、去重、抓取状态持久化。"""

import pytest

from news_watcher.models import NewsItem
from news_watcher.storage import Storage


@pytest.fixture
def storage():
    s = Storage(":memory:")
    yield s
    s.close()


def item(news_id: str, source: str = "s1") -> NewsItem:
    return NewsItem(
        id=news_id, title=f"t{news_id}", url="https://x.com", content="c", source=source
    )


def test_source_not_initialized_by_default(storage):
    assert not storage.is_initialized("s1")


def test_mark_initialized(storage):
    storage.mark_initialized("s1")
    assert storage.is_initialized("s1")


def test_filter_new_returns_unseen_items(storage):
    storage.save("s1", [item("a")])
    new = storage.filter_new("s1", [item("a"), item("b")])
    assert [it.id for it in new] == ["b"]


def test_filter_new_scoped_per_source(storage):
    storage.save("s1", [item("a", source="s1")])
    new = storage.filter_new("s2", [item("a", source="s2")])
    assert len(new) == 1


def test_save_ignores_duplicates(storage):
    assert storage.save("s1", [item("a")]) == 1
    assert storage.save("s1", [item("a")]) == 0


def test_save_stores_content(storage):
    storage.save("s1", [item("a")])
    row = storage._conn.execute("SELECT * FROM news WHERE news_id = 'a'").fetchone()
    assert row["title"] == "ta"
    assert row["content"] == "c"
    assert row["url"] == "https://x.com"


def test_state_roundtrip(storage):
    assert storage.get_state("s1") == {}
    storage.save_state("s1", {"entry_ids": ["a", "b"]})
    assert storage.get_state("s1") == {"entry_ids": ["a", "b"]}
    storage.save_state("s1", {"entry_ids": ["c"]})
    assert storage.get_state("s1") == {"entry_ids": ["c"]}


def test_state_scoped_per_source(storage):
    storage.save_state("s1", {"x": 1})
    assert storage.get_state("s2") == {}


def test_state_survives_mark_initialized(storage):
    storage.save_state("s1", {"x": 1})
    storage.mark_initialized("s1")
    assert storage.get_state("s1") == {"x": 1}
    assert storage.is_initialized("s1")


def test_db_file_created_in_dir(tmp_path):
    s = Storage(str(tmp_path / "subdir"))
    s.close()
    assert (tmp_path / "subdir" / "news_watcher.db").exists()
