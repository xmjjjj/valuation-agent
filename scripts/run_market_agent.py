"""单独运行市场环境 Agent。用法: python scripts/run_market_agent.py [patent_id]"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agents.innovation import innovation_agent
from src.agents.market import market_agent
from src.agents.scene import scene_agent
from src.repository import get_patent_data


def main() -> int:
    patent_id = sys.argv[1] if len(sys.argv) > 1 else "CN202320045678.9"
    try:
        patent = get_patent_data(patent_id)
        innovation = innovation_agent(patent)
        scene = scene_agent(patent, innovation)
        result = market_agent(patent, scene)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    payload = {
        "patent_id": patent.patent_id,
        "method": result.method,
        "market_score": result.market_score,
        "risk_index": result.risk_index,
        "risk_factors": result.risk_factors,
        "market_summary": result.market_summary,
        "breakdown": {
            "size_score": result.breakdown.size_score,
            "growth_score": result.breakdown.growth_score,
            "competition_score": result.breakdown.competition_score,
            "policy_score": result.breakdown.policy_score,
        },
        "scene_score_used": scene.scene_score,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
