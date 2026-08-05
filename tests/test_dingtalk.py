"""钉钉 target：消息体、加签与错误处理（respx mock HTTP）。"""

import urllib.parse

import httpx
import pytest
import respx

from news_watcher.models import NewsItem
from news_watcher.targets.dingtalk import DingTalkTarget


def make_target(secret: str = "") -> DingTalkTarget:
    return DingTalkTarget("dt", access_token="tok123", secret=secret)


def items() -> list[NewsItem]:
    return [
        NewsItem(id="1", title="标题一", url="https://a.com/1", content="内容一"),
        NewsItem(id="2", title="标题二", url="https://a.com/2", content=""),
    ]


def test_build_message_markdown():
    msg = DingTalkTarget.build_message(items())
    assert msg["msgtype"] == "markdown"
    text = msg["markdown"]["text"]
    assert "[标题一](https://a.com/1)" in text
    assert "2 条" in msg["markdown"]["title"]


def test_url_with_secret_sign():
    target = make_target(secret="SECabc")
    url = target._url()
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    assert query["access_token"] == ["tok123"]
    assert "timestamp" in query and "sign" in query


def test_url_without_secret_has_no_sign():
    url = make_target()._url()
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    assert "sign" not in query


@respx.mock
async def test_send_success():
    route = respx.post("https://oapi.dingtalk.com/robot/send").mock(
        return_value=httpx.Response(200, json={"errcode": 0, "errmsg": "ok"})
    )
    await make_target().send(items())
    assert route.called


@respx.mock
async def test_send_raises_on_dingtalk_error():
    respx.post("https://oapi.dingtalk.com/robot/send").mock(
        return_value=httpx.Response(200, json={"errcode": 310000, "errmsg": "keywords not in content"})
    )
    with pytest.raises(RuntimeError, match="钉钉机器人返回错误"):
        await make_target().send(items())


async def test_send_empty_items_no_request():
    with respx.mock(assert_all_called=False):
        await make_target().send([])
