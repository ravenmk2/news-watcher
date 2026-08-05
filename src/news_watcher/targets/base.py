"""投递目标抽象。"""

from abc import ABC, abstractmethod

from ..models import NewsItem


class Target(ABC):
    """一种投递目标组件。

    target 不一定是直接发通知：可以是机器人推送、日志打印、写文件、回调等。
    子类实现 `send()`；通过 `@register_target("type_name")` 注册后，
    可在配置中以 `type = "type_name"` 引用。同一类型可配置多个实例。
    """

    def __init__(self, name: str, **params):
        self.name = name

    @abstractmethod
    async def send(self, items: list[NewsItem]) -> None:
        """投递一批新条目。"""
