import argparse
import os
import sys

from watchpost.alerting import detect_transition
from watchpost.checker import check_all
from watchpost.config import ConfigError, load_config
from watchpost.history import connect, save_result
from watchpost.report import DEFAULT_WINDOW, build_report, format_report
from watchpost.webhook import WebhookError, build_message, send_alert


def any_down(results):
    return any(not r.success for r in results)


def load_webhook_url():
    """
    Reads WATCHPOST_WEBHOOK_URL from the environment. Doesn't touch .env
    itself - call load_dotenv() first if you want values from .env picked
    up. Kept separate so this stays a pure function tests can call without
    a real .env file lying around.
    """
    url = os.environ.get("WATCHPOST_WEBHOOK_URL")
    if not url:
        print("error: --alert needs WATCHPOST_WEBHOOK_URL set (add it to .env)", file=sys.stderr)
        return None
    return url


def cmd_check(args):
    try:
        endpoints = load_config(args.config)
    except ConfigError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    webhook_url = None
    if args.alert:
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            print("error: --alert needs python-dotenv - run: pip install python-dotenv", file=sys.stderr)
            return 1

        webhook_url = load_webhook_url()
        if webhook_url is None:
            return 1

    conn = connect(args.db)
    results = check_all(endpoints)

    for r in results:
        save_result(conn, r)  # save before checking history, so this check counts as "current"

        status = "DOWN" if not r.success else ("SLOW" if r.slow else "UP")
        code = r.status_code if r.status_code is not None else "-"
        print(f"{r.endpoint_name:<20} {status:<6} {code}")

        if webhook_url:
            transition = detect_transition(conn, r)
            if transition:
                try:
                    send_alert(webhook_url, build_message(r.endpoint_name, transition, r))
                except WebhookError as e:
                    print(f"warning: webhook alert failed: {e}", file=sys.stderr)

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
    check_parser = sub.add_parser("check", help="run a check against every endpoint and save the result")
    check_parser.add_argument("--alert", action="store_true",
                               help="send a webhook alert on down/recovery (needs WATCHPOST_WEBHOOK_URL in .env)")

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
