from __future__ import annotations

import argparse
import json
from datetime import date, timedelta

from .config import Settings
from .pipeline import collect_day, collect_history, run_demo


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Power BI usage monitoring pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo", help="Run with synthetic data")
    demo.add_argument("--output-dir", default="output")

    collect = subparsers.add_parser("collect", help="Collect Power BI administrative data")
    collect.add_argument("--date", dest="target_date")
    collect.add_argument("--history-days", type=int, default=1)
    collect.add_argument("--no-postgres", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "demo":
        result = run_demo(args.output_dir)
    else:
        settings = Settings.from_env(require_powerbi=True)
        sync_postgres = not args.no_postgres
        if args.target_date:
            result = collect_day(
                settings,
                date.fromisoformat(args.target_date),
                sync_postgres=sync_postgres,
            )
        elif args.history_days == 1:
            result = collect_day(
                settings,
                date.today() - timedelta(days=1),
                sync_postgres=sync_postgres,
            )
        else:
            result = collect_history(
                settings,
                args.history_days,
                sync_postgres=sync_postgres,
            )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
