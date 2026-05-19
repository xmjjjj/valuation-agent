"""
创新程度 Agent

输入：专利文本、元数据、引用次数、IPC 前沿标记、奖项信息
处理：LLM 提取创新点（未配置 API 时规则回退）
输出：创新分数、创新等级、关键技术点列表、分项得分
"""

from __future__ import annotations

import re

from src.config import (
    AWARD_SCORE,
    CITATION_SCORE_CAP,
    IPC_FRONTIER_SCORE,
    MAX_INNOVATION_POINTS,
    TEXT_SCORE_CAP,
)
from src.llm.client import chat_completion_json
from src.models import InnovationResult, InnovationScoreBreakdown, PatentData

# 创新等级阈值（方案）
LEVEL_HIGH_MIN = 71
LEVEL_MID_MIN = 41


def innovation_level(score: float) -> str:
    if score >= LEVEL_HIGH_MIN:
        return "高创新"
    if score >= LEVEL_MID_MIN:
        return "中创新"
    return "低创新"


def calc_text_score(point_count: int, max_points: int = MAX_INNOVATION_POINTS) -> float:
    """文本创新度分 = min(创新点数量 / 最大创新点数量 * 40, 40)"""
    if max_points <= 0:
        return 0.0
    return round(min(point_count / max_points * TEXT_SCORE_CAP, TEXT_SCORE_CAP), 2)


def calc_citation_score(citation_count: int, avg_citation: float) -> float:
    """引用量分 = min(被引用次数 / 行业平均被引用次数 * 30, 30)"""
    avg = max(float(avg_citation), 0.1)
    return round(min(citation_count / avg * CITATION_SCORE_CAP, CITATION_SCORE_CAP), 2)


def calc_ipc_score(is_frontier: bool) -> float:
    """IPC 前沿分：前沿 10，否则 0"""
    return float(IPC_FRONTIER_SCORE if is_frontier else 0)


def calc_award_score(has_award: bool) -> float:
    """奖项分：获奖 15，否则 0"""
    return float(AWARD_SCORE if has_award else 0)


def calc_innovation_score(
    point_count: int,
    citation_count: int,
    avg_citation: float,
    is_ipc_frontier: bool,
    has_award: bool,
) -> InnovationScoreBreakdown:
    breakdown = InnovationScoreBreakdown(
        text_score=calc_text_score(point_count),
        citation_score=calc_citation_score(citation_count, avg_citation),
        ipc_score=calc_ipc_score(is_ipc_frontier),
        award_score=calc_award_score(has_award),
    )
    return breakdown


def _total_score(breakdown: InnovationScoreBreakdown) -> float:
    total = (
        breakdown.text_score
        + breakdown.citation_score
        + breakdown.ipc_score
        + breakdown.award_score
    )
    return round(min(total, 100.0), 2)


def _build_llm_messages(patent: PatentData) -> list[dict[str, str]]:
    meta = (
        f"专利号: {patent.patent_id}\n"
        f"申请人: {patent.applicant}\n"
        f"发明人: {patent.inventor}\n"
        f"IPC: {patent.ipc_code}\n"
        f"授权年份: {patent.grant_year}\n"
        f"法律状态: {patent.legal_status}\n"
        f"被引用次数: {patent.citation_count}\n"
        f"是否获奖: {'是' if patent.has_award else '否'}\n"
    )
    user_content = (
        f"{meta}\n"
        f"标题: {patent.title}\n\n"
        f"摘要:\n{patent.abstract}\n\n"
        f"权利要求（节选）:\n{(patent.claims or '')[:4000]}\n\n"
        "请分析上述专利的技术创新点，输出 JSON，格式严格为：\n"
        '{"key_innovations": ["创新点1", "创新点2", ...], "summary": "一两句总评"}\n'
        f"要求：key_innovations 为 {1}~{MAX_INNOVATION_POINTS} 条，"
        "每条一句话，突出相对现有技术的区别；不要重复标题。"
    )
    return [
        {
            "role": "system",
            "content": (
                "你是知识产权与专利技术分析专家，擅长从专利文本中提取可量化的技术创新点。"
                "只返回合法 JSON，不要输出其它文字。"
            ),
        },
        {"role": "user", "content": user_content},
    ]


def _extract_innovations_llm(patent: PatentData) -> list[str] | None:
    data = chat_completion_json(_build_llm_messages(patent))
    if not data:
        return None
    raw = data.get("key_innovations") or data.get("innovation_points") or []
    if not isinstance(raw, list):
        return None
    points = [str(p).strip() for p in raw if str(p).strip()]
    return points[:MAX_INNOVATION_POINTS] or None


def _extract_innovations_rule(patent: PatentData) -> list[str]:
    """未配置 LLM 时的规则回退：摘要句 + 技术关键词。"""
    text = f"{patent.title}\n{patent.abstract}\n{patent.claims}"
    keywords = [
        "大语言模型",
        "LLM",
        "语言模型",
        "神经网络",
        "深度学习",
        "Transformer",
        "注意力机制",
        "知识图谱",
        "语义",
        "新型",
        "改进",
        "首次",
        "显著",
        "优化",
        "降低",
        "提高",
        "封装",
        "复合材料",
        "催化剂",
        "催化",
        "单体",
        "聚合",
        "官能团",
        "收率",
        "选择性",
        "电解液",
        "正极材料",
        "绿色合成",
    ]
    points: list[str] = []
    for sentence in re.split(r"[。；;.\n]", patent.abstract or ""):
        s = sentence.strip()
        if len(s) >= 12 and s not in points:
            points.append(s)
    for kw in keywords:
        if kw.lower() in text.lower() and kw not in points:
            points.append(f"涉及关键技术：{kw}")
    if patent.claims:
        first_claim = patent.claims.strip().splitlines()[0][:120]
        if first_claim and first_claim not in points:
            points.append(f"独立权利要求要点：{first_claim}")
    return points[:MAX_INNOVATION_POINTS] or ["文本未提取到明确创新点，建议补充权利要求或启用 LLM 分析"]


def innovation_agent(patent: PatentData) -> InnovationResult:
    """
    创新程度 Agent 主入口。

    创新分数 = 文本创新度分 + 引用量分 + IPC前沿分 + 奖项分
    """
    method = "rule"
    key_innovations = _extract_innovations_rule(patent)

    llm_points = _extract_innovations_llm(patent)
    if llm_points:
        key_innovations = llm_points
        method = "llm"

    point_count = len(key_innovations)
    breakdown = calc_innovation_score(
        point_count=point_count,
        citation_count=patent.citation_count,
        avg_citation=patent.avg_citation,
        is_ipc_frontier=patent.is_ipc_frontier,
        has_award=patent.has_award,
    )
    innovation_score = _total_score(breakdown)

    return InnovationResult(
        innovation_score=innovation_score,
        innovation_level=innovation_level(innovation_score),
        key_innovations=key_innovations,
        innovation_point_count=point_count,
        breakdown=breakdown,
        method=method,
    )
