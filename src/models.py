from dataclasses import dataclass, field
from typing import Any


@dataclass
class PatentData:
    patent_id: str
    title: str
    abstract: str
    claims: str
    applicant: str
    inventor: str
    ipc_code: str
    ipc_prefix: str
    grant_year: int | None
    legal_status: str
    citation_count: int
    has_award: bool
    avg_citation: float
    is_ipc_frontier: bool
    industry: dict[str, Any] | None = None


@dataclass
class InnovationScoreBreakdown:
    """创新分数分项（对应方案公式）。"""

    text_score: float = 0.0
    citation_score: float = 0.0
    ipc_score: float = 0.0
    award_score: float = 0.0


@dataclass
class InnovationResult:
    innovation_score: float
    innovation_level: str
    key_innovations: list[str]
    innovation_point_count: int
    breakdown: InnovationScoreBreakdown = field(default_factory=InnovationScoreBreakdown)
    method: str = "rule"  # llm | rule


@dataclass
class SceneResult:
    scene_labels: list[str]
    scene_score: float
    industry_maturity: str = "新兴"  # 成熟 | 新兴
    industry_summary: str = ""
    method: str = "rule"  # llm | rule
    innovation_score_used: float = 0.0


@dataclass
class MarketResult:
    market_score: float
    risk_index: float


@dataclass
class ValueResult:
    final_score: float
    valuation_wan: float
    pledge_amount_wan: float


@dataclass
class PipelineReport:
    patent_id: str
    title: str
    innovation: InnovationResult
    scene: SceneResult
    market: MarketResult
    value: ValueResult
    run_id: str
    report_text: str
    report_json: dict[str, Any] = field(default_factory=dict)
