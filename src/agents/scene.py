"""
应用场景 Agent

输入：创新程度 Agent 输出、专利文本、行业数据（作行业报告摘要）
处理：规则或 LLM 生成场景标签（可多标签），再计算落地分数
输出：scene_labels、scene_score、行业成熟度等
"""

from __future__ import annotations

from src.config import OPENAI_API_KEY
from src.llm.client import chat_completion_json
from src.models import InnovationResult, PatentData, SceneResult

# 规则：关键词 / IPC 前缀 -> 场景标签
SCENE_RULES: list[tuple[list[str], str]] = [
    (["大语言模型", "LLM", "语言模型", "专利", "知识产权", "G06N"], "人工智能/知识产权金融科技"),
    (["半导体", "封装", "芯片", "H01L"], "半导体制造与封装"),
    (["高分子", "复合材料", "聚合物", "C08F"], "新材料/化工"),
    (["医疗", "诊断", "生物", "A61"], "医疗健康"),
    (["电池", "储能", "新能源", "H01M"], "新能源与储能"),
    (["汽车", "车联网", "B60"], "智能网联汽车"),
]

# 行业成熟度：增长率低于阈值视为成熟（与方案「行业成熟/新兴」对应）
MATURITY_GROWTH_THRESHOLD = 10.0

# 落地分数区间（方案）
SCORE_BAND_HIGH_MATURE = (80.0, 100.0)
SCORE_BAND_HIGH_EMERGING = (60.0, 80.0)
SCORE_BAND_LOW = (20.0, 60.0)
INNOVATION_HIGH_THRESHOLD = 70.0


def industry_maturity(industry: dict | None) -> str:
    """根据行业增长率判断成熟 / 新兴。"""
    if not industry:
        return "新兴"
    growth = float(industry.get("growth_rate", 0))
    return "成熟" if growth < MATURITY_GROWTH_THRESHOLD else "新兴"


def build_industry_report_summary(industry: dict | None) -> str:
    """用库内行业数据生成简短「行业公开报告」摘要（基本版）。"""
    if not industry:
        return "暂无匹配行业数据，按新兴市场假设处理。"
    return (
        f"IPC行业段 {industry.get('ipc_prefix', '')}："
        f"市场规模约 {industry.get('market_size', 0)} 亿元，"
        f"增长率 {industry.get('growth_rate', 0)}%，"
        f"竞争程度 {industry.get('competition_level', '中')}，"
        f"政策支持度 {industry.get('policy_support', 0)}/100。"
    )


def _score_in_band(value: float, low: float, high: float) -> float:
    return round(max(low, min(high, value)), 2)


def calc_scene_score(innovation_score: float, maturity: str) -> float:
    """
    落地分数（落在方案区间内，随创新分微调）：

    - 创新 > 70 且成熟  -> 80~100
    - 创新 > 70 且新兴  -> 60~80
    - 创新 <= 70        -> 20~60
    """
    s = innovation_score
    if s > INNOVATION_HIGH_THRESHOLD:
        low, high = (
            SCORE_BAND_HIGH_MATURE if maturity == "成熟" else SCORE_BAND_HIGH_EMERGING
        )
        # 创新分 71~100 映射到区间 [low, high]
        ratio = (s - INNOVATION_HIGH_THRESHOLD) / (100 - INNOVATION_HIGH_THRESHOLD)
        return _score_in_band(low + ratio * (high - low), low, high)

    # 创新分 0~70 映射到 20~60
    low, high = SCORE_BAND_LOW
    ratio = s / INNOVATION_HIGH_THRESHOLD
    return _score_in_band(low + ratio * (high - low), low, high)


def _match_labels_rule(patent: PatentData) -> list[str]:
    text = f"{patent.title} {patent.abstract} {patent.claims} {patent.ipc_code}"
    labels: list[str] = []
    for keywords, label in SCENE_RULES:
        if any(kw in text for kw in keywords):
            if label not in labels:
                labels.append(label)
    ipc = (patent.ipc_prefix or patent.ipc_code or "").upper()
    if ipc.startswith("G06") and "人工智能/知识产权金融科技" not in labels:
        labels.append("人工智能/知识产权金融科技")
    return labels or ["通用工业应用"]


def _build_llm_messages(
    patent: PatentData,
    innovation: InnovationResult,
    industry_summary: str,
) -> list[dict[str, str]]:
    innovations = "；".join(innovation.key_innovations[:5])
    user = (
        f"专利标题: {patent.title}\n"
        f"摘要: {patent.abstract}\n"
        f"IPC: {patent.ipc_code}\n"
        f"创新分数: {innovation.innovation_score}（{innovation.innovation_level}）\n"
        f"主要创新点: {innovations}\n"
        f"行业报告摘要: {industry_summary}\n\n"
        "请给出该专利的主要应用场景标签（2~5个，可多标签），输出 JSON：\n"
        '{"scene_labels": ["场景1", "场景2"], "rationale": "一句话说明"}\n'
        "标签应具体可落地，如「智慧金融风控」「车规级芯片封装」等。"
    )
    return [
        {
            "role": "system",
            "content": "你是产业分析与专利商业化专家。只返回合法 JSON。",
        },
        {"role": "user", "content": user},
    ]


def _extract_labels_llm(
    patent: PatentData,
    innovation: InnovationResult,
    industry_summary: str,
) -> list[str] | None:
    if not OPENAI_API_KEY:
        return None
    data = chat_completion_json(_build_llm_messages(patent, innovation, industry_summary))
    if not data:
        return None
    raw = data.get("scene_labels") or []
    if not isinstance(raw, list):
        return None
    labels = [str(x).strip() for x in raw if str(x).strip()]
    return labels[:8] or None


def scene_agent(patent: PatentData, innovation: InnovationResult) -> SceneResult:
    """应用场景 Agent 主入口。"""
    industry_summary = build_industry_report_summary(patent.industry)
    maturity = industry_maturity(patent.industry)

    method = "rule"
    labels = _match_labels_rule(patent)
    llm_labels = _extract_labels_llm(patent, innovation, industry_summary)
    if llm_labels:
        labels = llm_labels
        method = "llm"

    scene_score = calc_scene_score(innovation.innovation_score, maturity)

    return SceneResult(
        scene_labels=labels,
        scene_score=scene_score,
        industry_maturity=maturity,
        industry_summary=industry_summary,
        method=method,
        innovation_score_used=innovation.innovation_score,
    )
