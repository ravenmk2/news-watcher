"""智谱（zhipu / bigmodel）新品发布来源。

抓取 https://docs.bigmodel.cn/cn/update/new-releases（Mintlify 静态页面），
每个 `div.update-container` 更新块解析为一条新闻。支持状态过滤：state 中持久化
已见条目 id 列表，fetch 只返回新条目。
"""

import hashlib
from typing import Any

import httpx
from bs4 import BeautifulSoup

from ..models import NewsItem
from . import register_source
from .base import FetchResult, NewsSource

DEFAULT_URL = "https://docs.bigmodel.cn/cn/update/new-releases"
CONTENT_MAX_LEN = 500


@register_source("zhipu_release")
class ZhipuReleaseSource(NewsSource):
    supports_state = True

    def __init__(self, name: str, url: str = DEFAULT_URL, **params):
        super().__init__(name, **params)
        self.url = url

    async def fetch(self, state: dict[str, Any]) -> FetchResult:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(self.url)
            resp.raise_for_status()
        entries = self.parse(resp.text)
        if not entries:
            raise RuntimeError(f"未从 {self.url} 解析到任何更新条目，页面结构可能已变化")

        seen = set(state.get("entry_ids", []))
        new_items = [it for it in entries if it.id not in seen]
        new_state = {"entry_ids": [it.id for it in entries]}
        return FetchResult(items=new_items, state=new_state)

    def parse(self, html: str) -> list[NewsItem]:
        """把页面解析为条目列表（全部，不过滤）。拆出来便于测试。"""
        soup = BeautifulSoup(html, "html.parser")
        items = []
        for block in soup.select("div.update-container"):
            date = block.get("id") or ""
            label = block.select_one('[data-component-part="update-label"]')
            desc = block.select_one('[data-component-part="update-description"]')
            content_el = block.select_one('[data-component-part="update-content"]')
            if not date or desc is None or content_el is None:
                continue
            title = desc.get_text(strip=True)
            content = content_el.get_text(" ", strip=True)[:CONTENT_MAX_LEN]
            digest_src = f"{title}{content}"
            entry_id = f"{date}:{hashlib.sha1(digest_src.encode()).hexdigest()[:8]}"
            items.append(
                NewsItem(
                    id=entry_id,
                    title=title,
                    url=f"{self.url}#{date}",
                    content=content,
                    source=self.name,
                )
            )
        return items
