"""来源注册表与工厂。新增来源：在子模块中用 @register_source 注册并在此导入。"""

from __future__ import annotations

from typing import Callable

from ..config import SourceConfig
from .base import NewsSource

_REGISTRY: dict[str, type[NewsSource]] = {}


def register_source(type_name: str) -> Callable[[type[NewsSource]], type[NewsSource]]:
    def deco(cls: type[NewsSource]) -> type[NewsSource]:
        _REGISTRY[type_name] = cls
        return cls

    return deco


def build_source(name: str, cfg: SourceConfig) -> NewsSource:
    if cfg.type not in _REGISTRY:
        raise ValueError(f"未知的来源类型: {cfg.type}（可用: {sorted(_REGISTRY)}）")
    return _REGISTRY[cfg.type](name, **cfg.params)


def available_types() -> list[str]:
    return sorted(_REGISTRY)


# 触发各来源子模块的注册
from . import demo, deepseek, zhipu  # noqa: E402, F401
