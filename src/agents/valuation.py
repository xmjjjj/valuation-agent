"""
估值 Agent

输入：价值整合 Agent 的综合评分、行业估值上限（max_market_value，万元）
处理：
  valuation = final_score / 100 * max_market_value
  pledge_amount = valuation * pledge_ratio（默认 0.7）
"""

from __future__ import annotations

from src.config import DEFAULT_MAX_MARKET_VALUE_WAN, PLEDGE_RATIO
from src.models import ValuationResult, ValueIntegrationResult


def resolve_max_market_value(industry: dict | None) -> float:
    """按行业市场规模设定估值上限（万元）。"""
    if not industry:
        return DEFAULT_MAX_MARKET_VALUE_WAN
    explicit = industry.get("max_market_value")
    if explicit is not None and float(explicit) > 0:
        return float(explicit)
    # 无配置时：以行业规模（亿元）* 10 作为参考上限，并设下限
    market_size = float(industry.get("market_size", 0))
    derived = market_size * 10
    return max(derived, DEFAULT_MAX_MARKET_VALUE_WAN / 2)


def valuation_agent(
    integration: ValueIntegrationResult,
    industry: dict | None,
    *,
    pledge_ratio: float = PLEDGE_RATIO,
) -> ValuationResult:
    """估值 Agent 主入口。"""
    max_market_value = resolve_max_market_value(industry)
    valuation = round(integration.final_score / 100 * max_market_value, 2)
    pledge_amount = round(valuation * pledge_ratio, 2)

    return ValuationResult(
        valuation_wan=valuation,
        pledge_amount_wan=pledge_amount,
        max_market_value_wan=max_market_value,
        pledge_ratio=pledge_ratio,
    )
