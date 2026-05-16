import json
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from src.config import REPORTS_DIR
from src.models import (
    InnovationResult,
    MarketResult,
    PatentData,
    PipelineReport,
    SceneResult,
    ValueResult,
)


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
    score_detail = (
        f"文本{bd.text_score}+引用{bd.citation_score}+IPC{bd.ipc_score}+奖项{bd.award_score}"
    )
    return (
        f"专利名称: {patent.title}\n"
        f"创新分析（{innovation.method}）: {innovations}\n"
        f"创新分数 {innovation.innovation_score}（{innovation.innovation_level}），分项 {score_detail}\n"
        f"应用场景（{scene.method}，行业{scene.industry_maturity}）: {labels}，落地度 {scene.scene_score}\n"
        f"行业参考: {scene.industry_summary}\n"
        f"市场分析: 市场潜力 {market.market_score}，风险 {market.risk_index}\n"
        f"估值及质押: {value.valuation_wan} 万元，质押额度 {value.pledge_amount_wan} 万元\n"
        f"综合评分: {value.final_score}\n"
    )


def _write_pdf(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    y = height - 50
    for line in text.splitlines():
        pdf.drawString(50, y, line[:90])
        y -= 20
        if y < 50:
            pdf.showPage()
            y = height - 50
    pdf.save()


def report_agent(
    patent: PatentData,
    innovation: InnovationResult,
    scene: SceneResult,
    market: MarketResult,
    value: ValueResult,
    run_id: str,
) -> PipelineReport:
    report_text = _build_report_text(patent, innovation, scene, market, value)
    report_json = {
        "run_id": run_id,
        "patent_id": patent.patent_id,
        "title": patent.title,
        "innovation_score": innovation.innovation_score,
        "innovation_level": innovation.innovation_level,
        "key_innovations": innovation.key_innovations,
        "scene_labels": scene.scene_labels,
        "scene_score": scene.scene_score,
        "market_score": market.market_score,
        "risk_index": market.risk_index,
        "final_score": value.final_score,
        "valuation_wan": value.valuation_wan,
        "pledge_amount_wan": value.pledge_amount_wan,
        "report_text": report_text,
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_DIR / f"{patent.patent_id}_{run_id}.json"
    pdf_path = REPORTS_DIR / f"{patent.patent_id}_{run_id}.pdf"
    json_path.write_text(json.dumps(report_json, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_pdf(pdf_path, report_text)

    return PipelineReport(
        patent_id=patent.patent_id,
        title=patent.title,
        innovation=innovation,
        scene=scene,
        market=market,
        value=value,
        run_id=run_id,
        report_text=report_text,
        report_json=report_json,
    )
