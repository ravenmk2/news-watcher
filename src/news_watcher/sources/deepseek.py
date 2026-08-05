"""DeepSeek API 文档更新日志来源。

抓取 https://api-docs.deepseek.com/zh-cn/updates（Docusaurus 静态页面），
每个 `时间: YYYY-MM-DD` 小节解析为一条新闻。支持状态过滤：state 中持久化
已见条目 id 列表，fetch 只返回新条目。
"""

import hashlib
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup, Tag

from ..models import NewsItem
from . import register_source
from .base import FetchResult, NewsSource

DEFAULT_URL = "https://api-docs.deepseek.com/zh-cn/updates"
CONTENT_MAX_LEN = 500
_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


@register_source("deepseek_update")
class DeepSeekUpdateSource(NewsSource):
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
        container = soup.select_one(".theme-doc-markdown") or soup
        items = []
        for h2 in container.find_all("h2"):
            date = self._date_of(h2)
            if date is None:
                continue
            # 收集该 h2 到下一个 h2 之间的内容
            section = []
            for sib in h2.find_next_siblings():
                if not isinstance(sib, Tag):
                    continue
                if sib.name == "h2":
                    break
                section.append(sib)

            h3s = []
            for sib in section:
                if sib.name == "h3":
                    h3s.append(sib)  # h3 与 h2 平级时，sib 自身即标题
                else:
                    h3s.extend(sib.find_all("h3"))
            title = h3s[0].get_text(strip=True) if h3s else f"时间: {date}"
            digest_src = ",".join(h.get("id", "") for h in h3s) or "".join(
                sib.get_text() for sib in section
            )[:200]
            entry_id = f"{date}:{hashlib.sha1(digest_src.encode()).hexdigest()[:8]}"
            content = " ".join(
                sib.get_text(" ", strip=True) for sib in section
            )[:CONTENT_MAX_LEN]
            items.append(
                NewsItem(
                    id=entry_id,
                    title=title,
                    url=f"{self.url}#{h2.get('id', '')}",
                    content=content,
                    source=self.name,
                )
            )
        return items

    @staticmethod
    def _date_of(h2: Tag) -> str | None:
        """从 h2 的 id 或文本中提取日期，非更新条目小节返回 None。"""
        anchor = h2.get("id") or ""
        text = h2.get_text()
        if "时间" not in anchor and "时间" not in text:
            return None
        match = _DATE_RE.search(anchor) or _DATE_RE.search(text)
        return match.group(1) if match else None
