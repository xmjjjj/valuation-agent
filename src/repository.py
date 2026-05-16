from sqlalchemy import text

from src.db import get_session
from src.models import PatentData


def _ipc_prefix(ipc_code: str) -> str:
    code = (ipc_code or "").replace(" ", "").upper()
    if len(code) >= 4:
        letters = "".join(ch for ch in code[:4] if ch.isalpha())
        if len(letters) >= 3:
            return letters[:4]
        return code[:4]
    return code[:4] if code else ""


def get_patent_data(patent_id: str) -> PatentData:
    sql = text(
        """
        SELECT
            p.patent_id,
            p.title,
            p.abstract,
            p.claims,
            p.applicant,
            p.inventor,
            p.ipc_code,
            p.grant_year,
            p.legal_status,
            p.citation_count,
            p.has_award,
            COALESCE(s.avg_citation, 1) AS avg_citation,
            COALESCE(f.is_frontier, 0) AS is_frontier,
            i.ipc_prefix AS industry_ipc,
            i.market_size,
            i.growth_rate,
            i.competition_level,
            i.policy_support,
            i.max_market_value
        FROM patents p
        LEFT JOIN ipc_citation_stats s
            ON s.ipc_prefix = LEFT(REPLACE(p.ipc_code, ' ', ''), 4)
           AND s.grant_year = p.grant_year
        LEFT JOIN ipc_frontier f
            ON f.ipc_code = LEFT(REPLACE(p.ipc_code, ' ', ''), 4)
        LEFT JOIN industry_data i
            ON i.ipc_prefix = LEFT(REPLACE(p.ipc_code, ' ', ''), 4)
        WHERE p.patent_id = :patent_id
        """
    )

    with get_session() as session:
        row = session.execute(sql, {"patent_id": patent_id}).mappings().first()

    if not row:
        raise ValueError(f"Patent not found: {patent_id}")

    prefix = _ipc_prefix(row["ipc_code"] or "")
    industry = None
    if row.get("industry_ipc"):
        industry = {
            "ipc_prefix": row["industry_ipc"],
            "market_size": float(row["market_size"] or 0),
            "growth_rate": float(row["growth_rate"] or 0),
            "competition_level": row["competition_level"] or "中",
            "policy_support": int(row["policy_support"] or 0),
            "max_market_value": float(row["max_market_value"] or 10000),
        }

    return PatentData(
        patent_id=row["patent_id"],
        title=row["title"] or "",
        abstract=row["abstract"] or "",
        claims=row["claims"] or "",
        applicant=row["applicant"] or "",
        inventor=row["inventor"] or "",
        ipc_code=row["ipc_code"] or "",
        ipc_prefix=prefix,
        grant_year=row["grant_year"],
        legal_status=row["legal_status"] or "",
        citation_count=int(row["citation_count"] or 0),
        has_award=bool(row["has_award"]),
        avg_citation=float(row["avg_citation"] or 1),
        is_ipc_frontier=bool(row["is_frontier"]),
        industry=industry,
    )
