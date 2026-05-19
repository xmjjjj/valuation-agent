"""可选：用数据库中的行业/引用统计 enrich 文件导入的专利（库不可用时静默跳过）。"""

from __future__ import annotations

from sqlalchemy import text

from src.models import PatentData
from src.repository import _ipc_prefix


def enrich_patent_from_db(patent: PatentData) -> PatentData:
    """若 MySQL 可用，按 IPC 补全行业参数、前沿标记、平均引用。"""
    if not patent.ipc_code:
        return patent

    try:
        from src.db import get_session
    except Exception:
        return patent

    prefix = patent.ipc_prefix or _ipc_prefix(patent.ipc_code)
    avg_citation = patent.avg_citation
    is_frontier = patent.is_ipc_frontier
    industry = patent.industry

    try:
        with get_session() as session:
            ind = session.execute(
                text(
                    """
                    SELECT ipc_prefix, market_size, growth_rate, competition_level,
                           policy_support, max_market_value
                    FROM industry_data WHERE ipc_prefix = :ipc_prefix
                    """
                ),
                {"ipc_prefix": prefix},
            ).mappings().first()
            if ind and not industry:
                industry = {
                    "ipc_prefix": ind["ipc_prefix"],
                    "market_size": float(ind["market_size"] or 0),
                    "growth_rate": float(ind["growth_rate"] or 0),
                    "competition_level": ind["competition_level"] or "中",
                    "policy_support": int(ind["policy_support"] or 0),
                    "max_market_value": float(ind["max_market_value"] or 10000),
                }

            fr = session.execute(
                text("SELECT is_frontier FROM ipc_frontier WHERE ipc_code = :ipc_prefix"),
                {"ipc_prefix": prefix},
            ).first()
            if fr:
                is_frontier = bool(fr[0])

            if patent.grant_year is not None:
                stat = session.execute(
                    text(
                        """
                        SELECT avg_citation FROM ipc_citation_stats
                        WHERE ipc_prefix = :ipc_prefix AND grant_year = :grant_year
                        """
                    ),
                    {"ipc_prefix": prefix, "grant_year": patent.grant_year},
                ).first()
                if stat:
                    avg_citation = float(stat[0])
    except Exception:
        return patent

    return PatentData(
        patent_id=patent.patent_id,
        title=patent.title,
        abstract=patent.abstract,
        claims=patent.claims,
        applicant=patent.applicant,
        inventor=patent.inventor,
        ipc_code=patent.ipc_code,
        ipc_prefix=prefix,
        grant_year=patent.grant_year,
        legal_status=patent.legal_status,
        citation_count=patent.citation_count,
        has_award=patent.has_award,
        avg_citation=avg_citation,
        is_ipc_frontier=is_frontier,
        industry=industry,
    )
