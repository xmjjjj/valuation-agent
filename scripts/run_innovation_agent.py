"""
单独运行创新程度 Agent。

用法:
  python scripts/run_innovation_agent.py
  python scripts/run_innovation_agent.py CN202310001234.5
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agents.innovation import innovation_agent
from src.config import OPENAI_API_KEY
from src.repository import get_patent_data


def main() -> int:
    patent_id = sys.argv[1] if len(sys.argv) > 1 else "CN202310001234.5"
    try:
        patent = get_patent_data(patent_id)
        result = innovation_agent(patent)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    payload = {
        "patent_id": patent.patent_id,
        "title": patent.title,
        "method": result.method,
        "llm_configured": bool(OPENAI_API_KEY),
        "innovation_score": result.innovation_score,
        "innovation_level": result.innovation_level,
        "innovation_point_count": result.innovation_point_count,
        "key_innovations": result.key_innovations,
        "breakdown": {
            "text_score": result.breakdown.text_score,
            "citation_score": result.breakdown.citation_score,
            "ipc_score": result.breakdown.ipc_score,
            "award_score": result.breakdown.award_score,
        },
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
