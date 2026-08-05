"""target 注册表与工厂。新增 target 类型：在子模块中用 @register_target 注册并在此导入。"""

from __future__ import annotations

from typing import Callable

from ..config import TargetConfig
from .base import Target

_REGISTRY: dict[str, type[Target]] = {}


def register_target(type_name: str) -> Callable[[type[Target]], type[Target]]:
    def deco(cls: type[Target]) -> type[Target]:
        _REGISTRY[type_name] = cls
        return cls

    return deco


def build_target(name: str, cfg: TargetConfig) -> Target:
    if cfg.type not in _REGISTRY:
        raise ValueError(f"未知的 target 类型: {cfg.type}（可用: {sorted(_REGISTRY)}）")
    return _REGISTRY[cfg.type](name, **cfg.params)


def available_types() -> list[str]:
    return sorted(_REGISTRY)


# 触发各 target 子模块的注册
from . import dingtalk, print  # noqa: E402, F401
