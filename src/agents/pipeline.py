"""
多 Agent 估值流水线

专利数据 → 创新程度 → 应用场景 → 市场环境 → 价值整合 → 估值 → 报告
"""

from __future__ import annotations

import json
import uuid

from sqlalchemy import text

from src.agents.innovation import innovation_agent
from src.agents.market import market_agent
from src.agents.report import report_agent
from src.agents.scene import scene_agent
from src.agents.valuation import valuation_agent
from src.agents.value import value_integration_agent
from src.db import get_session
from src.models import PatentData, PipelineReport, ValueResult
from src.repository import get_patent_data


def run_pipeline_on_patent(patent: PatentData, *, save: bool = False) -> PipelineReport:
    """对已构造的 PatentData 运行六 Agent 流水线（不查 patents 表）。"""
    innovation = innovation_agent(patent)
    scene = scene_agent(patent, innovation)
    market = market_agent(patent, scene)
    integration = value_integration_agent(innovation, scene, market)
    valuation = valuation_agent(integration, patent.industry)
    value = ValueResult(integration=integration, valuation=valuation)

    run_id = str(uuid.uuid4())
    report = report_agent(patent, innovation, scene, market, value, run_id)
    if save:
        _save_run(report)
    return report


def _save_run(report: PipelineReport) -> None:
    sql = text(
        """
        INSERT INTO valuation_runs (
            run_id, patent_id,
            innovation_score, innovation_level, key_innovations,
            scene_labels, scene_score,
            market_score, risk_index,
            final_score, valuation_wan, pledge_amount_wan,
            report_json
        ) VALUES (
            :run_id, :patent_id,
            :innovation_score, :innovation_level, :key_innovations,
            :scene_labels, :scene_score,
            :market_score, :risk_index,
            :final_score, :valuation_wan, :pledge_amount_wan,
            :report_json
        )
        """
    )
    payload = {
        "run_id": report.run_id,
        "patent_id": report.patent_id,
        "innovation_score": report.innovation.innovation_score,
        "innovation_level": report.innovation.innovation_level,
        "key_innovations": json.dumps(report.innovation.key_innovations, ensure_ascii=False),
        "scene_labels": json.dumps(report.scene.scene_labels, ensure_ascii=False),
        "scene_score": report.scene.scene_score,
        "market_score": report.market.market_score,
        "risk_index": report.market.risk_index,
        "final_score": report.value.final_score,
        "valuation_wan": report.value.valuation_wan,
        "pledge_amount_wan": report.value.pledge_amount_wan,
        "report_json": json.dumps(report.report_json, ensure_ascii=False),
    }
    with get_session() as session:
        session.execute(sql, payload)
        session.commit()


def run_pipeline(patent_id: str, *, save: bool = True) -> PipelineReport:
    return run_pipeline_on_patent(get_patent_data(patent_id), save=save)


def run_pipeline_from_file(
    file_path: str,
    *,
    save: bool = False,
    use_llm_parse: bool = True,
    enrich_db: bool = True,
) -> PipelineReport:
    """从本地 txt/json/pdf 加载专利并估值（默认不写库，避免外键约束）。"""
    from src.ingest.enrich import enrich_patent_from_db
    from src.ingest.file_loader import load_patent_from_file

    patent = load_patent_from_file(file_path, use_llm=use_llm_parse)
    if enrich_db:
        patent = enrich_patent_from_db(patent)
    return run_pipeline_on_patent(patent, save=save)
