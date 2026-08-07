"""核心流程：抓取 → 去重（首抓忽略）→ 按规则分发到各 target。"""

from __future__ import annotations

import asyncio

from loguru import logger

from .config import RuleConfig
from .models import NewsItem
from .sources.base import NewsSource
from .storage import Storage
from .targets.base import Target


def targets_for(
    source_name: str, rules: dict[str, RuleConfig]
) -> dict[str, list[str]]:
    """返回 {规则名: [target 名, ...]}（仅匹配该来源的规则）。"""
    return {
        name: rule.targets
        for name, rule in rules.items()
        if source_name in rule.sources
    }


async def run_source(
    source: NewsSource,
    storage: Storage,
    targets: dict[str, Target],
    rules: dict[str, RuleConfig],
) -> list[NewsItem]:
    """执行一轮来源抓取，返回本轮的新条目（首抓返回空列表）。"""
    state = storage.get_state(source.name)
    result = await source.fetch(state)
    logger.info("来源 {} 抓取到 {} 条", source.name, len(result.items))

    if not storage.is_initialized(source.name):
        inserted = storage.save(source.name, result.items)
        storage.mark_initialized(source.name)
        storage.save_state(source.name, result.state)
        logger.info(
            "来源 {} 首次抓取，{} 条已入库作为基线，不触发投递", source.name, inserted
        )
        return []

    if source.supports_state:
        # 来源已用状态过滤，返回即新条目（入库仍 INSERT OR IGNORE 兜底）
        new_items = result.items
    else:
        new_items = storage.filter_new(source.name, result.items)
    storage.save(source.name, new_items)
    storage.save_state(source.name, result.state)

    if not new_items:
        logger.info("来源 {} 无新条目", source.name)
        return []
    logger.info("来源 {} 发现 {} 条新条目", source.name, len(new_items))

    matched_rules = targets_for(source.name, rules)
    if not matched_rules:
        logger.warning("来源 {} 没有匹配的规则", source.name)
        return new_items

    # 按规则分组投递：同一 target 在多规则下会收到各自规则的投递
    send_tasks = []
    owners = []
    for rule_name, target_names in matched_rules.items():
        for target_name in target_names:
            target = targets.get(target_name)
            if target is None:
                logger.warning("规则 {} 的 target {} 未配置，跳过", rule_name, target_name)
                continue
            send_tasks.append(target.send(new_items))
            owners.append(f"{rule_name}/{target_name}")
    results = await asyncio.gather(*send_tasks, return_exceptions=True)
    for owner, result in zip(owners, results):
        if isinstance(result, Exception):
            logger.error("规则 {} 投递失败: {}", owner, result)
    return new_items


async def run_source_safe(
    source: NewsSource,
    storage: Storage,
    targets: dict[str, Target],
    rules: dict[str, RuleConfig],
) -> list[NewsItem]:
    """带异常隔离的一轮抓取，供调度器调用。"""
    try:
        return await run_source(source, storage, targets, rules)
    except Exception as exc:
        logger.exception("来源 {} 抓取失败: {}", source.name, exc)
        return []
