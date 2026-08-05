"""SQLite 存储：新闻条目入库 + 来源状态（首抓标记 / 抓取状态）。"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Iterable

from .models import NewsItem

DB_FILENAME = "news_watcher.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    news_id TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    content TEXT NOT NULL,
    first_seen_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_news_source_news_id ON news(source, news_id);

CREATE TABLE IF NOT EXISTS source_state (
    source TEXT PRIMARY KEY,
    initialized INTEGER NOT NULL DEFAULT 0,
    state TEXT NOT NULL DEFAULT '{}'
);
"""


class Storage:
    """基于 sqlite3 的轻量存储，单连接 + 锁，供异步代码中直接调用（操作均为毫秒级）。

    传入数据目录，数据库文件名固定为 news_watcher.db；目录传 ":memory:" 时使用内存库（测试用）。
    """

    def __init__(self, directory: str):
        if directory == ":memory:":
            path = directory
        else:
            dir_path = Path(directory)
            dir_path.mkdir(parents=True, exist_ok=True)
            path = str(dir_path / DB_FILENAME)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._migrate()
            self._conn.commit()

    def _migrate(self) -> None:
        """老库迁移：补齐 source_state 缺失的列。"""
        cols = {
            row["name"]
            for row in self._conn.execute("PRAGMA table_info(source_state)")
        }
        if "state" not in cols:
            self._conn.execute(
                "ALTER TABLE source_state ADD COLUMN state TEXT NOT NULL DEFAULT '{}'"
            )

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ---- 来源状态 ----

    def is_initialized(self, source: str) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT initialized FROM source_state WHERE source = ?", (source,)
            ).fetchone()
        return bool(row and row["initialized"])

    def mark_initialized(self, source: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO source_state(source, initialized) VALUES (?, 1) "
                "ON CONFLICT(source) DO UPDATE SET initialized = 1",
                (source,),
            )
            self._conn.commit()

    def get_state(self, source: str) -> dict:
        """读取来源的抓取状态，无记录时返回空 dict。"""
        with self._lock:
            row = self._conn.execute(
                "SELECT state FROM source_state WHERE source = ?", (source,)
            ).fetchone()
        return json.loads(row["state"]) if row else {}

    def save_state(self, source: str, state: dict) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO source_state(source, state) VALUES (?, ?) "
                "ON CONFLICT(source) DO UPDATE SET state = excluded.state",
                (source, json.dumps(state, ensure_ascii=False)),
            )
            self._conn.commit()

    # ---- 新闻条目 ----

    def filter_new(self, source: str, items: Iterable[NewsItem]) -> list[NewsItem]:
        """返回该来源尚未入库的条目。"""
        items = list(items)
        if not items:
            return []
        placeholders = ",".join("?" for _ in items)
        with self._lock:
            rows = self._conn.execute(
                f"SELECT news_id FROM news WHERE source = ? AND news_id IN ({placeholders})",
                (source, *(it.id for it in items)),
            ).fetchall()
        seen = {row["news_id"] for row in rows}
        return [it for it in items if it.id not in seen]

    def save(self, source: str, items: Iterable[NewsItem]) -> int:
        """批量入库，已存在的 (source, news_id) 忽略。返回实际插入条数。"""
        items = list(items)
        if not items:
            return 0
        with self._lock:
            cur = self._conn.executemany(
                "INSERT OR IGNORE INTO news(source, news_id, title, url, content) "
                "VALUES (?, ?, ?, ?, ?)",
                [(source, it.id, it.title, it.url, it.content) for it in items],
            )
            self._conn.commit()
        return cur.rowcount
