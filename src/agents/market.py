from src.models import MarketResult, PatentData, SceneResult

COMPETITION_SCORE = {"低": 20, "中": 10, "高": 0}


def market_agent(patent: PatentData, scene: SceneResult) -> MarketResult:
    industry = patent.industry or {
        "market_size": 500,
        "growth_rate": 8,
        "competition_level": "中",
    }

    market_size = float(industry.get("market_size", 500))
    growth_rate = float(industry.get("growth_rate", 8))
    competition = str(industry.get("competition_level", "中"))

    size_score = min(market_size / 1000 * 50, 50)
    growth_score = min(growth_rate * 2, 30)
    competition_score = COMPETITION_SCORE.get(competition, 10)

    market_score = round(size_score + growth_score + competition_score, 2)
    market_score = min(market_score, 100)
    risk_index = round(100 - market_score, 2)

    return MarketResult(market_score=market_score, risk_index=risk_index)
