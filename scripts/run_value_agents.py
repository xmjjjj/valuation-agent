"""单独运行价值整合 + 估值 Agent。用法: python scripts/run_value_agents.py [patent_id]"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agents.innovation import innovation_agent
from src.agents.market import market_agent
from src.agents.scene import scene_agent
from src.agents.valuation import valuation_agent
from src.agents.value import value_integration_agent
from src.repository import get_patent_data


def main() -> int:
    patent_id = sys.argv[1] if len(sys.argv) > 1 else "CN202320045678.9"
    try:
        patent = get_patent_data(patent_id)
        innovation = innovation_agent(patent)
        scene = scene_agent(patent, innovation)
        market = market_agent(patent, scene)
        integration = value_integration_agent(innovation, scene, market)
        valuation = valuation_agent(integration, patent.industry)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    payload = {
        "patent_id": patent.patent_id,
        "integration": {
            "final_score_raw": integration.final_score_raw,
            "final_score": integration.final_score,
            "innovation_weighted": integration.innovation_weighted,
            "scene_weighted": integration.scene_weighted,
            "market_weighted": integration.market_weighted,
            "risk_adjustment_factor": integration.risk_adjustment_factor,
        },
        "valuation": {
            "max_market_value_wan": valuation.max_market_value_wan,
            "valuation_wan": valuation.valuation_wan,
            "pledge_amount_wan": valuation.pledge_amount_wan,
            "pledge_ratio": valuation.pledge_ratio,
        },
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
