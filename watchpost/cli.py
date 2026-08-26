import argparse
import sys

from watchpost.checker import check_all
from watchpost.config import ConfigError, load_config
from watchpost.history import connect, save_all
from watchpost.report import DEFAULT_WINDOW, build_report, format_report


def any_down(results):
    return any(not r.success for r in results)


def cmd_check(args):
    try:
        endpoints = load_config(args.config)
    except ConfigError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    results = check_all(endpoints)
    save_all(connect(args.db), results)

    for r in results:
        status = "DOWN" if not r.success else ("SLOW" if r.slow else "UP")
        code = r.status_code if r.status_code is not None else "-"
        print(f"{r.endpoint_name:<20} {status:<6} {code}")

    # non-zero only for a real failure, not a slow warning - keeps this
    # usable as a cron/CI gate without a latency blip failing the job
    return 1 if any_down(results) else 0


def cmd_report(args):
    try:
        endpoints = load_config(args.config)
    except ConfigError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    conn = connect(args.db)
    reports = build_report(conn, endpoints, window=args.window)
    print(format_report(reports))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="watchpost")
    parser.add_argument("--config", default="config.yaml", help="path to endpoints config (default: config.yaml)")
    parser.add_argument("--db", default="data/history.db", help="path to history db (default: data/history.db)")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="run a check against every endpoint and save the result")

    report_parser = sub.add_parser("report", help="show current status and recent incidents")
    report_parser.add_argument("--window", type=int, default=DEFAULT_WINDOW,
                                help=f"how many recent checks to look at (default: {DEFAULT_WINDOW})")

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "check":
        return cmd_check(args)
    return cmd_report(args)


if __name__ == "__main__":
    sys.exit(main())
