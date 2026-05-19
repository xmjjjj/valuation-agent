"""
价值整合 Agent

输入：创新分数、场景落地分、市场潜力分、风险指数
处理（Python 确定性计算）：
  final_score_raw = 0.4*innovation + 0.3*scene + 0.3*market
  final_score = final_score_raw * (1 - risk_index/100)
"""

from __future__ import annotations

from src.config import (
    VALUE_WEIGHT_INNOVATION,
    VALUE_WEIGHT_MARKET,
    VALUE_WEIGHT_SCENE,
)
from src.models import (
    InnovationResult,
    MarketResult,
    SceneResult,
    ValueIntegrationResult,
)


def value_integration_agent(
    innovation: InnovationResult,
    scene: SceneResult,
    market: MarketResult,
) -> ValueIntegrationResult:
    """价值整合 Agent 主入口。"""
    innovation_w = round(innovation.innovation_score * VALUE_WEIGHT_INNOVATION, 4)
    scene_w = round(scene.scene_score * VALUE_WEIGHT_SCENE, 4)
    market_w = round(market.market_score * VALUE_WEIGHT_MARKET, 4)

    final_score_raw = round(innovation_w + scene_w + market_w, 2)
    risk_factor = round(1 - market.risk_index / 100, 4)
    risk_factor = max(0.0, min(1.0, risk_factor))
    final_score = round(final_score_raw * risk_factor, 2)
    final_score = max(0.0, min(final_score, 100.0))

    return ValueIntegrationResult(
        final_score_raw=final_score_raw,
        final_score=final_score,
        innovation_weighted=innovation_w,
        scene_weighted=scene_w,
        market_weighted=market_w,
        risk_adjustment_factor=risk_factor,
    )
