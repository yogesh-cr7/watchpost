from datetime import datetime, timezone

from watchpost.history import recent_checks

DEFAULT_WINDOW = 20  # gut feeling, not measured - bump this or make it a flag if it turns out wrong


def endpoint_report(conn, endpoint, window=DEFAULT_WINDOW):
    checks = recent_checks(conn, endpoint.name, limit=window)
    if not checks:
        return {
            "name": endpoint.name,
            "status": "NO DATA",
            "status_code": None,
            "latency_ms": None,
            "uptime_pct": None,
            "incidents": [],
        }

    latest = checks[0]  # recent_checks orders newest first
    uptime_pct = round(100 * sum(c.success for c in checks) / len(checks), 1)

    # a slow check isn't a failure - it still counts toward uptime - but it's
    # still worth surfacing alongside real incidents
    incidents = [c for c in checks if not c.success or c.slow]

    if not latest.success:
        status = "DOWN"
    elif latest.slow:
        status = "SLOW"
    else:
        status = "UP"

    return {
        "name": endpoint.name,
        "status": status,
        "status_code": latest.status_code,
        "latency_ms": latest.latency_ms,
        "uptime_pct": uptime_pct,
        "incidents": incidents,
    }


def build_report(conn, endpoints, window=DEFAULT_WINDOW):
    # walk the config, not just whatever's in the db, so a brand new endpoint
    # shows up as "no data" instead of silently not appearing at all
    return [endpoint_report(conn, e, window=window) for e in endpoints]


def format_report(reports):
    lines = []
    for r in reports:
        if r["status"] == "NO DATA":
            lines.append(f"{r['name']:<20} NO DATA")
            continue

        code = r["status_code"] if r["status_code"] is not None else "-"
        latency = f"{r['latency_ms']}ms" if r["latency_ms"] is not None else "-"
        lines.append(f"{r['name']:<20} {r['status']:<6} {str(code):<5} {latency:<8} uptime: {r['uptime_pct']}%")

    incidents = [(r["name"], c) for r in reports for c in r["incidents"]]
    if incidents:
        lines.append("")
        lines.append("recent incidents:")
        for name, c in incidents:
            when = datetime.fromtimestamp(c.timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            if not c.success:
                reason = c.error if c.error else f"got {c.status_code}"
            else:
                reason = f"slow ({c.latency_ms}ms)"
            lines.append(f"  {name:<15} {when}   {reason}")

    return "\n".join(lines)
