"""
报告生成 Agent

输入：各 Agent 输出、专利摘要
处理：模板填充 → 可选 LLM 润色可读性 → 输出 JSON 与 PDF
"""

from __future__ import annotations

import json
from pathlib import Path

from src.config import OPENAI_API_KEY, REPORTS_DIR
from src.llm.client import chat_completion_text
from src.models import (
    InnovationResult,
    MarketResult,
    PatentData,
    PipelineReport,
    SceneResult,
    ValueResult,
)

# 常见 Noto CJK 路径（Docker / Linux / Windows）
_CJK_FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
]


def _resolve_cjk_font() -> Path | None:
    for p in _CJK_FONT_CANDIDATES:
        path = Path(p)
        if path.is_file():
            return path
    return None


def _build_report_text(
    patent: PatentData,
    innovation: InnovationResult,
    scene: SceneResult,
    market: MarketResult,
    value: ValueResult,
) -> str:
    labels = "、".join(scene.scene_labels)
    innovations = "；".join(innovation.key_innovations)
    bd = innovation.breakdown
    mbd = market.breakdown
    score_detail = (
        f"文本{bd.text_score}+引用{bd.citation_score}+IPC{bd.ipc_score}+奖项{bd.award_score}"
    )
    market_detail = (
        f"规模{mbd.size_score}+增长{mbd.growth_score}"
        f"+竞争{mbd.competition_score}+政策{mbd.policy_score}"
    )
    risks = "；".join(market.risk_factors)
    vi = value.integration
    val = value.valuation

    return (
        f"专利名称: {patent.title}\n"
        f"专利号: {patent.patent_id}\n"
        f"IPC分类: {patent.ipc_code}  申请人: {patent.applicant}\n\n"
        f"【创新分析】（{innovation.method}）\n"
        f"{innovations}\n"
        f"创新分数 {innovation.innovation_score}（{innovation.innovation_level}），分项 {score_detail}\n\n"
        f"【应用场景】（{scene.method}，行业{scene.industry_maturity}）\n"
        f"场景标签: {labels}\n"
        f"落地度 {scene.scene_score}\n"
        f"{scene.industry_summary}\n\n"
        f"【市场分析】（{market.method}）\n"
        f"{market.market_summary}\n"
        f"市场潜力 {market.market_score}（{market_detail}），风险指数 {market.risk_index}\n"
        f"风险因素: {risks}\n\n"
        f"【价值整合】\n"
        f"加权原始分 {vi.final_score_raw}，风险调整后综合分 {vi.final_score}\n"
        f"（创新×0.4 + 场景×0.3 + 市场×0.3，再×{vi.risk_adjustment_factor}）\n\n"
        f"【估值及质押】\n"
        f"行业估值上限 {val.max_market_value_wan} 万元\n"
        f"估值 {val.valuation_wan} 万元，质押额度 {val.pledge_amount_wan} 万元（质押率 {val.pledge_ratio:.0%}）\n"
    )


def _build_llm_polish_messages(draft: str, patent: PatentData) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "你是专利价值评估报告撰写专家，面向化学化工领域投资与质押场景。"
                "在保持所有数字、分数、万元金额不变的前提下，将报告改写得条理清晰、专业可读。"
                "只输出润色后的正文，不要 JSON，不要编造新数据。"
            ),
        },
        {
            "role": "user",
            "content": f"专利摘要供参考：{patent.abstract[:800]}\n\n请润色以下报告：\n\n{draft}",
        },
    ]


def _polish_report_llm(draft: str, patent: PatentData) -> str | None:
    if not OPENAI_API_KEY:
        return None
    content = chat_completion_text(
        _build_llm_polish_messages(draft, patent),
        temperature=0.3,
    )
    if content and len(content.strip()) > 50:
        return content.strip()
    return None


def _write_text_report(path: Path, text: str) -> Path:
    """始终写入 UTF-8 文本报告（避免中文 PDF 编码失败）。"""
    txt_path = path.with_suffix(".txt")
    txt_path.write_text(text, encoding="utf-8")
    return txt_path


def _write_pdf(path: Path, text: str) -> None:
    """生成 UTF-8 文本报告；PDF 易因 latin-1/字体在 Windows 失败，默认不写 PDF。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_text_report(path, text)


def report_agent(
    patent: PatentData,
    innovation: InnovationResult,
    scene: SceneResult,
    market: MarketResult,
    value: ValueResult,
    run_id: str,
) -> PipelineReport:
    """报告生成 Agent 主入口。"""
    report_text = _build_report_text(patent, innovation, scene, market, value)
    polished = _polish_report_llm(report_text, patent)
    report_text_final = polished or report_text
    polish_method = "llm" if polished else "template"

    vi = value.integration
    val = value.valuation
    report_json = {
        "run_id": run_id,
        "patent_id": patent.patent_id,
        "title": patent.title,
        "ipc_code": patent.ipc_code,
        "applicant": patent.applicant,
        "innovation_score": innovation.innovation_score,
        "innovation_level": innovation.innovation_level,
        "key_innovations": innovation.key_innovations,
        "innovation_breakdown": {
            "text_score": innovation.breakdown.text_score,
            "citation_score": innovation.breakdown.citation_score,
            "ipc_score": innovation.breakdown.ipc_score,
            "award_score": innovation.breakdown.award_score,
        },
        "scene_labels": scene.scene_labels,
        "scene_score": scene.scene_score,
        "industry_maturity": scene.industry_maturity,
        "market_score": market.market_score,
        "market_breakdown": {
            "size_score": market.breakdown.size_score,
            "growth_score": market.breakdown.growth_score,
            "competition_score": market.breakdown.competition_score,
            "policy_score": market.breakdown.policy_score,
        },
        "market_summary": market.market_summary,
        "risk_index": market.risk_index,
        "risk_factors": market.risk_factors,
        "final_score_raw": vi.final_score_raw,
        "final_score": vi.final_score,
        "max_market_value_wan": val.max_market_value_wan,
        "valuation_wan": val.valuation_wan,
        "pledge_amount_wan": val.pledge_amount_wan,
        "report_text": report_text_final,
        "report_polish_method": polish_method,
        "agents": {
            "innovation": innovation.method,
            "scene": scene.method,
            "market": market.method,
            "report": polish_method,
        },
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    # 文件名仅用 run_id，避免专利号/中文标题导致 Windows 路径或 latin-1 编码错误
    json_path = REPORTS_DIR / f"{run_id}.json"
    pdf_path = REPORTS_DIR / f"{run_id}.pdf"
    json_path.write_text(
        json.dumps(report_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_pdf(pdf_path, report_text_final)

    return PipelineReport(
        patent_id=patent.patent_id,
        title=patent.title,
        innovation=innovation,
        scene=scene,
        market=market,
        value=value,
        run_id=run_id,
        report_text=report_text,
        report_text_polished=report_text_final,
        report_json=report_json,
    )
