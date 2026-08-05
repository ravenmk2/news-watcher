"""deepseek_update 来源：页面解析与状态过滤。"""

import httpx
import pytest
import respx

from news_watcher.sources.deepseek import DEFAULT_URL, DeepSeekUpdateSource

FIXTURE_HTML = """
<html><body>
<div class="theme-doc-markdown markdown">
  <h2 class="anchor" id="时间-2026-07-31">时间: 2026-07-31</h2>
  <h3 class="anchor" id="deepseek-v4-flash-更新">DeepSeek-V4-Flash 更新</h3>
  <p>DeepSeek-V4-Flash 正式版 API 上线公测。</p>
  <h2 class="anchor" id="时间-2026-04-24">时间: 2026-04-24</h2>
  <h3 class="anchor" id="deepseek-v4">DeepSeek-V4</h3>
  <p>DeepSeek API 已支持 V4-Pro 与 V4-Flash。</p>
  <h3 class="anchor" id="v4-extra">补充说明</h3>
  <p>旧模型名将停用。</p>
  <h2 class="anchor" id="其他小节">其他</h2>
  <p>不是更新条目，应被忽略。</p>
</div>
</body></html>
"""


def make_source() -> DeepSeekUpdateSource:
    return DeepSeekUpdateSource("deepseek")


def test_parse_entries():
    items = make_source().parse(FIXTURE_HTML)
    assert len(items) == 2  # "其他" 小节被忽略

    first = items[0]
    assert first.id.startswith("2026-07-31:")
    assert first.title == "DeepSeek-V4-Flash 更新"
    assert "正式版 API 上线公测" in first.content
    assert first.url.startswith(DEFAULT_URL)
    assert first.source == "deepseek"

    # 同一日期下多个 h3 仍是一条条目，id 与单 h3 小节不同
    second = items[1]
    assert second.id.startswith("2026-04-24:")
    assert second.id != first.id
    assert "旧模型名将停用" in second.content


def test_parse_ids_stable():
    a = [it.id for it in make_source().parse(FIXTURE_HTML)]
    b = [it.id for it in make_source().parse(FIXTURE_HTML)]
    assert a == b


@respx.mock
async def test_fetch_filters_by_state():
    respx.get(DEFAULT_URL).mock(
        return_value=httpx.Response(200, text=FIXTURE_HTML)
    )
    source = make_source()

    result = await source.fetch({})
    assert len(result.items) == 2
    assert result.state["entry_ids"] == [it.id for it in result.items]

    # 状态中的条目被过滤，无新条目
    result2 = await source.fetch(result.state)
    assert result2.items == []

    # 部分已见时只返回未见条目
    one_seen = {"entry_ids": [result.state["entry_ids"][0]]}
    result3 = await source.fetch(one_seen)
    assert len(result3.items) == 1
    assert result3.items[0].id == result.state["entry_ids"][1]


@respx.mock
async def test_fetch_raises_when_no_entries():
    respx.get(DEFAULT_URL).mock(
        return_value=httpx.Response(200, text="<html><body>empty</body></html>")
    )
    with pytest.raises(RuntimeError, match="未从 .* 解析到任何更新条目"):
        await make_source().fetch({})
