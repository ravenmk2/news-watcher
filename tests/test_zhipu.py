"""zhipu_release 来源：页面解析与状态过滤。"""

import httpx
import pytest
import respx

from news_watcher.sources.zhipu import DEFAULT_URL, ZhipuReleaseSource

FIXTURE_HTML = """
<html><body>
<div class="update update-container" id="2026-06-16">
  <button data-component-part="update-label">2026-06-16</button>
  <div data-component-part="update-description">GLM-5.2 新一代旗舰模型上线</div>
  <div data-component-part="update-content">
    <span>💬 GLM-5.2</span>
    <ul><li>支持 1M 无损上下文</li><li>Coding 能力提升</li></ul>
  </div>
</div>
<div class="update update-container" id="2026-05-29">
  <button data-component-part="update-label">2026-05-29</button>
  <div data-component-part="update-description">GLM Coding Plan 团队版上线</div>
  <div data-component-part="update-content">
    <ul><li>面向企业与开发团队的自助订阅方案上线</li></ul>
  </div>
</div>
<div class="other-block" id="not-an-update">
  <p>不是更新条目，应被忽略。</p>
</div>
</body></html>
"""


def make_source() -> ZhipuReleaseSource:
    return ZhipuReleaseSource("zhipu")


def test_parse_entries():
    items = make_source().parse(FIXTURE_HTML)
    assert len(items) == 2  # 非 update-container 块被忽略

    first = items[0]
    assert first.id.startswith("2026-06-16:")
    assert first.title == "GLM-5.2 新一代旗舰模型上线"
    assert "支持 1M 无损上下文" in first.content
    assert first.url == f"{DEFAULT_URL}#2026-06-16"
    assert first.source == "zhipu"

    second = items[1]
    assert second.id.startswith("2026-05-29:")
    assert second.id != first.id
    assert second.title == "GLM Coding Plan 团队版上线"


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
