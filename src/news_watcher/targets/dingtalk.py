"""钉钉自定义机器人 target（webhook + access_token，可选加签）。"""

import base64
import hashlib
import hmac
import time
import urllib.parse

import httpx
from loguru import logger

from ..models import NewsItem
from . import register_target
from .base import Target

WEBHOOK = "https://oapi.dingtalk.com/robot/send"


@register_target("dingtalk")
class DingTalkTarget(Target):
    def __init__(self, name: str, access_token: str, secret: str = "", **params):
        super().__init__(name, **params)
        self.access_token = access_token
        self.secret = secret

    def _url(self) -> str:
        params = {"access_token": self.access_token}
        if self.secret:
            timestamp = str(round(time.time() * 1000))
            string_to_sign = f"{timestamp}\n{self.secret}"
            sign = urllib.parse.quote_plus(
                base64.b64encode(
                    hmac.new(
                        self.secret.encode(), string_to_sign.encode(), hashlib.sha256
                    ).digest()
                )
            )
            params.update(timestamp=timestamp, sign=sign)
        return f"{WEBHOOK}?{urllib.parse.urlencode(params)}"

    @staticmethod
    def build_message(items: list[NewsItem]) -> dict:
        lines = [f"### 新闻速递（{len(items)} 条）\n"]
        for it in items:
            lines.append(f"- [{it.title}]({it.url})")
            if it.content:
                summary = it.content[:100] + ("…" if len(it.content) > 100 else "")
                lines.append(f"  > {summary}")
        return {
            "msgtype": "markdown",
            "markdown": {"title": f"新闻速递（{len(items)} 条）", "text": "\n".join(lines)},
        }

    async def send(self, items: list[NewsItem]) -> None:
        if not items:
            return
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(self._url(), json=self.build_message(items))
            resp.raise_for_status()
            data = resp.json()
        if data.get("errcode") != 0:
            raise RuntimeError(f"钉钉机器人返回错误: {data}")
        logger.info("target {} 已推送 {} 条新闻", self.name, len(items))
