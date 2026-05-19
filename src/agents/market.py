"""
市场环境 Agent

输入：应用场景 Agent 输出、专利行业数据（规模、增长率、竞争、政策支持）
处理：按方案计算市场潜力分；风险指数 = 100 - 市场分（并叠加场景落地不足惩罚）
输出：market_score、risk_index、分项得分、风险因素、市场摘要（可选 LLM）
"""

from __future__ import annotations

from src.config import (
    MARKET_COMPETITION_SCORE,
    MARKET_GROWTH_SCORE_CAP,
    MARKET_POLICY_SCORE_CAP,
    MARKET_SIZE_SCORE_CAP,
    OPENAI_API_KEY,
)
from src.llm.client import chat_completion_json
from src.models import MarketResult, MarketScoreBreakdown, PatentData, SceneResult

DEFAULT_INDUSTRY = {
    "market_size": 500.0,
    "growth_rate": 8.0,
    "competition_level": "中",
    "policy_support": 50,
    "ipc_prefix": "",
}


def calc_size_score(market_size: float) -> float:
    """市场规模分 = min(market_size / 1000 * 50, 50)（亿元）"""
    return round(min(market_size / 1000 * MARKET_SIZE_SCORE_CAP, MARKET_SIZE_SCORE_CAP), 2)


def calc_growth_score(growth_rate: float) -> float:
    """增长率分 = min(growth_rate * 2, 30)，growth_rate 为百分数如 8.5"""
    return round(min(growth_rate * 2, MARKET_GROWTH_SCORE_CAP), 2)


def calc_competition_score(level: str) -> float:
    """竞争调整分：低 20 / 中 10 / 高 0"""
    return float(MARKET_COMPETITION_SCORE.get(level, 10))


def calc_policy_score(policy_support: int) -> float:
    """政策支持附加分（化学等领域），0~10"""
    return round(min(max(policy_support, 0) / 10, MARKET_POLICY_SCORE_CAP), 2)


def calc_market_breakdown(industry: dict) -> MarketScoreBreakdown:
    market_size = float(industry.get("market_size", 500))
    growth_rate = float(industry.get("growth_rate", 8))
    competition = str(industry.get("competition_level", "中"))
    policy_support = int(industry.get("policy_support", 0))

    return MarketScoreBreakdown(
        size_score=calc_size_score(market_size),
        growth_score=calc_growth_score(growth_rate),
        competition_score=calc_competition_score(competition),
        policy_score=calc_policy_score(policy_support),
    )


def calc_market_score(breakdown: MarketScoreBreakdown) -> float:
    total = (
        breakdown.size_score
        + breakdown.growth_score
        + breakdown.competition_score
        + breakdown.policy_score
    )
    return round(min(total, 100.0), 2)


def calc_risk_index(
    market_score: float,
    scene_score: float,
    competition_level: str,
) -> tuple[float, list[str]]:
    """
    风险指数：以 100 - market_score 为基础，场景落地不足时上调风险。
    """
    risk = 100 - market_score
    factors: list[str] = []

    if market_score < 40:
        factors.append("行业市场潜力偏低")
    if scene_score < 50:
        penalty = round((50 - scene_score) * 0.15, 2)
        risk += penalty
        factors.append(f"应用场景落地度不足（scene_score={scene_score}）")
    if competition_level == "高":
        factors.append("行业竞争激烈")
    if not factors:
        factors.append("市场风险与行业潜力基本匹配")

    risk_index = round(max(0.0, min(100.0, risk)), 2)
    return risk_index, factors


def _build_rule_summary(industry: dict, breakdown: MarketScoreBreakdown) -> str:
    return (
        f"IPC {industry.get('ipc_prefix', '—')} 化工/相关行业："
        f"市场规模约 {industry.get('market_size', 0)} 亿元，"
        f"增长率 {industry.get('growth_rate', 0)}%，"
        f"竞争 {industry.get('competition_level', '中')}，"
        f"政策支持 {industry.get('policy_support', 0)}/100；"
        f"潜力分 {calc_market_score(breakdown)}"
        f"（规模{breakdown.size_score}+增长{breakdown.growth_score}"
        f"+竞争{breakdown.competition_score}+政策{breakdown.policy_score}）。"
    )


def _build_llm_messages(
    patent: PatentData,
    scene: SceneResult,
    industry: dict,
    breakdown: MarketScoreBreakdown,
) -> list[dict[str, str]]:
    labels = "、".join(scene.scene_labels)
    user = (
        f"专利: {patent.title}\n"
        f"IPC: {patent.ipc_code}\n"
        f"应用场景: {labels}（落地分 {scene.scene_score}，行业{scene.industry_maturity}）\n"
        f"行业数据: 规模 {industry.get('market_size')} 亿元，"
        f"增长 {industry.get('growth_rate')}%，竞争 {industry.get('competition_level')}，"
        f"政策支持 {industry.get('policy_support')}/100\n"
        f"已算市场潜力分: {calc_market_score(breakdown)}\n\n"
        "请从化学/新材料产业视角写 2~3 句市场分析，输出 JSON：\n"
        '{"market_summary": "分析正文", "outlook": "乐观|中性|谨慎"}\n'
    )
    return [
        {
            "role": "system",
            "content": "你是化工与新材料行业市场分析专家。只返回合法 JSON。",
        },
        {"role": "user", "content": user},
    ]


def _llm_market_summary(
    patent: PatentData,
    scene: SceneResult,
    industry: dict,
    breakdown: MarketScoreBreakdown,
) -> str | None:
    if not OPENAI_API_KEY:
        return None
    data = chat_completion_json(_build_llm_messages(patent, scene, industry, breakdown))
    if not data:
        return None
    summary = str(data.get("market_summary", "")).strip()
    outlook = str(data.get("outlook", "")).strip()
    if summary and outlook:
        return f"{summary}（前景：{outlook}）"
    return summary or None


def market_agent(patent: PatentData, scene: SceneResult) -> MarketResult:
    """市场环境 Agent 主入口。"""
    industry = dict(patent.industry or DEFAULT_INDUSTRY)
    if patent.ipc_prefix and not industry.get("ipc_prefix"):
        industry["ipc_prefix"] = patent.ipc_prefix

    breakdown = calc_market_breakdown(industry)
    market_score = calc_market_score(breakdown)
    competition = str(industry.get("competition_level", "中"))
    risk_index, risk_factors = calc_risk_index(
        market_score, scene.scene_score, competition
    )

    method = "rule"
    market_summary = _build_rule_summary(industry, breakdown)
    llm_summary = _llm_market_summary(patent, scene, industry, breakdown)
    if llm_summary:
        market_summary = llm_summary
        method = "llm"

    return MarketResult(
        market_score=market_score,
        risk_index=risk_index,
        breakdown=breakdown,
        market_summary=market_summary,
        risk_factors=risk_factors,
        method=method,
    )
