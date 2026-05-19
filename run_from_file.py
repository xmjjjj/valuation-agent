"""
从本地专利文件直接估值（无需 patents 表中有记录）。

用法:
  python run_from_file.py samples/patent_example.txt
  python run_from_file.py 你的专利.txt --no-llm
  python run_from_file.py 材料.pdf --enrich-db
"""

from __future__ import annotations

import argparse
import json
import sys

from src.agents.pipeline import run_pipeline_from_file


def main() -> int:
    parser = argparse.ArgumentParser(
        description="从本地 txt/md/json/pdf 运行六 Agent 专利估值"
    )
    parser.add_argument("file", help="专利文件路径 (.txt / .json / .pdf)")
    parser.add_argument(
        "--save-db",
        action="store_true",
        help="将结果写入 valuation_runs（需数据库已建表且 patent_id 满足外键）",
    )
    parser.add_argument(
        "--no-llm-parse",
        action="store_true",
        help="禁用 LLM 辅助解析字段",
    )
    parser.add_argument(
        "--no-enrich-db",
        action="store_true",
        help="不按 IPC 从数据库补充行业参数",
    )
    args = parser.parse_args()

    try:
        report = run_pipeline_from_file(
            args.file,
            save=args.save_db,
            use_llm_parse=not args.no_llm_parse,
            enrich_db=not args.no_enrich_db,
        )
    except Exception as exc:
        import traceback

        print(f"Error: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 1

    print(report.report_text_polished or report.report_text)
    print("--- JSON ---")
    print(json.dumps(report.report_json, ensure_ascii=False, indent=2))
    print(f"\n综合分: {report.value.final_score}  估值: {report.value.valuation_wan} 万元")
    print(f"报告已保存: ./reports/ (run_id={report.run_id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
