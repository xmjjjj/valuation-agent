"""
单独运行应用场景 Agent（会先跑创新程度 Agent）。

用法:
  python scripts/run_scene_agent.py
  python scripts/run_scene_agent.py CN202310001234.5
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agents.innovation import innovation_agent
from src.agents.scene import scene_agent
from src.config import OPENAI_API_KEY
from src.repository import get_patent_data


def main() -> int:
    patent_id = sys.argv[1] if len(sys.argv) > 1 else "CN202310001234.5"
    try:
        patent = get_patent_data(patent_id)
        innovation = innovation_agent(patent)
        scene = scene_agent(patent, innovation)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    payload = {
        "patent_id": patent.patent_id,
        "title": patent.title,
        "innovation_score": innovation.innovation_score,
        "innovation_level": innovation.innovation_level,
        "scene_labels": scene.scene_labels,
        "scene_score": scene.scene_score,
        "industry_maturity": scene.industry_maturity,
        "industry_summary": scene.industry_summary,
        "method": scene.method,
        "llm_configured": bool(OPENAI_API_KEY),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
