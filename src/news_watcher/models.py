"""核心数据模型。"""

from pydantic import BaseModel


class NewsItem(BaseModel):
    """一条新闻。`id` 由来源组件保证在该来源内唯一。"""

    id: str
    title: str
    url: str
    content: str
    source: str = ""
