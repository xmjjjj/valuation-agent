import argparse
import json
import sys

from src.agents.pipeline import run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Patent LLM agent valuation pipeline")
    parser.add_argument(
        "patent_id",
        nargs="?",
        default="CN202310001234.5",
        help="Patent ID, e.g. CN202310001234.5",
    )
    args = parser.parse_args()

    try:
        report = run_pipeline(args.patent_id)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(report.report_text)
    print("--- JSON ---")
    print(json.dumps(report.report_json, ensure_ascii=False, indent=2))
    print(f"\nReports saved under ./reports/ (run_id={report.run_id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
