"""配置加载：TOML 文件 + pydantic 校验，端口支持环境变量覆盖。"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

DEFAULT_CONFIG_PATH = "config.toml"
CONFIG_PATH_ENV = "NEWS_WATCHER_CONFIG"
PORT_ENV = "NEWS_WATCHER_PORT"


class ServerConfig(BaseModel):
    port: int = 8000


class StorageConfig(BaseModel):
    """数据目录；数据库文件名固定为 news_watcher.db。"""

    dir: str = "data"


class SourceConfig(BaseModel):
    """一种来源的实例配置；type 之外的字段作为 params 传给来源组件。"""

    model_config = ConfigDict(extra="allow")

    type: str
    cron: str

    @property
    def params(self) -> dict[str, Any]:
        return (self.model_extra or {}).copy()


class TargetConfig(BaseModel):
    """一个投递目标的实例配置；type 之外的字段作为 params 传给 target 组件。"""

    model_config = ConfigDict(extra="allow")

    type: str

    @property
    def params(self) -> dict[str, Any]:
        return (self.model_extra or {}).copy()


class RuleConfig(BaseModel):
    sources: list[str]
    targets: list[str]


class AppConfig(BaseModel):
    server: ServerConfig = ServerConfig()
    storage: StorageConfig = StorageConfig()
    sources: dict[str, SourceConfig] = {}
    targets: dict[str, TargetConfig] = {}
    rules: dict[str, RuleConfig] = {}

    @model_validator(mode="after")
    def _check_rule_refs(self) -> "AppConfig":
        for name, rule in self.rules.items():
            for source in rule.sources:
                if source not in self.sources:
                    raise ValueError(f"规则 {name} 引用了未配置的来源: {source}")
            for target in rule.targets:
                if target not in self.targets:
                    raise ValueError(f"规则 {name} 引用了未配置的 target: {target}")
        return self


def load_config(path: str | Path | None = None) -> AppConfig:
    """加载 TOML 配置。路径优先级：参数 > NEWS_WATCHER_CONFIG > config.toml。"""
    path = Path(path or os.environ.get(CONFIG_PATH_ENV, DEFAULT_CONFIG_PATH))
    with path.open("rb") as f:
        data = tomllib.load(f)
    config = AppConfig.model_validate(data)
    if port_env := os.environ.get(PORT_ENV):
        config.server.port = int(port_env)
    return config
