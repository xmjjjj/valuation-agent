"""
测试 DeepSeek 是否配置正确（会打印详细错误）。

用法:
  python scripts/test_deepseek.py
  python scripts/test_deepseek.py --model deepseek-v4-flash
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

parser = argparse.ArgumentParser()
parser.add_argument("--model", default="", help="临时覆盖 OPENAI_MODEL")
args = parser.parse_args()
if args.model:
    os.environ["OPENAI_MODEL"] = args.model

from src.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
from src.llm.client import chat_completion_json, get_last_error


def main() -> int:
    if not OPENAI_API_KEY:
        print("未配置 OPENAI_API_KEY，请在 .env 中设置。")
        return 1

    masked = (
        OPENAI_API_KEY[:7] + "..." + OPENAI_API_KEY[-4:]
        if len(OPENAI_API_KEY) > 12
        else "(too short)"
    )
    print(f"BASE_URL: {OPENAI_BASE_URL}")
    print(f"MODEL:    {OPENAI_MODEL}")
    print(f"API_KEY:  {masked}")
    print("请求中...")

    data = chat_completion_json(
        [
            {"role": "system", "content": "You must reply with valid JSON only."},
            {
                "role": "user",
                "content": 'Return JSON: {"status": "ok", "message": "DeepSeek connected"}',
            },
        ]
    )
    if data:
        print("成功:", data)
        return 0

    print("调用失败。")
    err = get_last_error()
    if err:
        print("--- 详细错误 ---")
        print(err)

    print("\n常见处理：")
    print("  401 / invalid_api_key  -> 到 platform.deepseek.com 重新创建 Key 并更新 .env")
    print("  402 / insufficient     -> 账户充值")
    print("  网络错误               -> 检查代理/VPN 或换热点")
    print("  模型不存在             -> 试: python scripts/test_deepseek.py --model deepseek-v4-flash")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
