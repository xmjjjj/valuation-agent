import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def _env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "patent")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "patent_dev")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "patent_valuation")

DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
)

REPORTS_DIR = PROJECT_ROOT / "reports"

# LLM（创新程度 Agent 等可选启用）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

# 创新程度 Agent 计分参数（与方案一致）
MAX_INNOVATION_POINTS = int(os.getenv("MAX_INNOVATION_POINTS", "8"))
TEXT_SCORE_CAP = 40
CITATION_SCORE_CAP = 30
IPC_FRONTIER_SCORE = 10
AWARD_SCORE = 15
