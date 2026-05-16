import json
import uuid

from sqlalchemy import text

from src.agents.innovation import innovation_agent
from src.agents.market import market_agent
from src.agents.report import report_agent
from src.agents.scene import scene_agent
from src.agents.value import value_agent
from src.db import get_session
from src.models import PipelineReport
from src.repository import get_patent_data


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


def run_pipeline(patent_id: str) -> PipelineReport:
    patent_data = get_patent_data(patent_id)
    innovation = innovation_agent(patent_data)
    scene = scene_agent(patent_data, innovation)
    market = market_agent(patent_data, scene)

    max_market_value = 10000.0
    if patent_data.industry:
        max_market_value = float(patent_data.industry.get("max_market_value", 10000))

    value = value_agent(innovation, scene, market, max_market_value)
    run_id = str(uuid.uuid4())
    report = report_agent(patent_data, innovation, scene, market, value, run_id)
    _save_run(report)
    return report
