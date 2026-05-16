from src.models import InnovationResult, MarketResult, SceneResult, ValueResult


def value_agent(
    innovation: InnovationResult,
    scene: SceneResult,
    market: MarketResult,
    max_market_value: float,
) -> ValueResult:
    final_score_raw = (
        0.4 * innovation.innovation_score
        + 0.3 * scene.scene_score
        + 0.3 * market.market_score
    )
    final_score = round(final_score_raw * (1 - market.risk_index / 100), 2)
    final_score = max(0, min(final_score, 100))

    valuation = round(final_score / 100 * max_market_value, 2)
    pledge_amount = round(valuation * 0.7, 2)

    return ValueResult(
        final_score=final_score,
        valuation_wan=valuation,
        pledge_amount_wan=pledge_amount,
    )
