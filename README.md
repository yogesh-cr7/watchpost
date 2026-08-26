# watchpost

*A CLI that watches your API endpoints, keeps a local uptime/latency
history, and can explain a failure in plain English instead of just a
status code.*

watchpost polls a list of API endpoints on a schedule, checks them against
expected status codes and latency thresholds, and logs the results locally.
When something breaks, it alerts you - and with an optional LLM step, tells
you what likely went wrong instead of leaving you to read a stack trace.

## why

I wanted something that pages me when a service I depend on goes down,
instead of finding out from a broken build or an angry curl mid-demo. Most
tools in this space are either full observability platforms (overkill for
watching a handful of endpoints) or a cron job piping curl into a log file
(no history, no trends, no context on why something failed). This sits in
between - point it at a small config of endpoints, it checks them on a
schedule, keeps a local history, and can optionally ask an LLM to read a
failure and explain it in plain English.

## plan

- [x] YAML config: endpoints to watch, expected status code, timeout, check interval
- [x] polling engine that hits each endpoint and records status + latency
- [x] local history (sqlite) so uptime/latency show trends, not just the last check
- [x] CLI report command - current status and recent incidents per endpoint
- [x] rule-based alerting when a check fails or latency crosses a threshold
- [ ] optional webhook alert (Slack/Discord) behind a flag
- [ ] optional LLM diagnosis behind a flag - reads a failure (status, body, recent history) and writes a plain-english guess at what went wrong
- [ ] packaging - installable CLI, entry point
- [ ] tests alongside each feature
- [ ] polish pass - license, real verified usage output, known-limitations section

## setup

```bash
pip install -r requirements.txt
```

Run a check against the bundled demo config (a few public APIs, no auth
needed) and save the results:

```bash
python -m watchpost.cli check
```

See current status, uptime over the last 20 checks per endpoint, and any
recent failures or slow responses:

```bash
python -m watchpost.cli report
```

```
github-status        UP     200   280.0ms  uptime: 100.0%
jsonplaceholder      SLOW   200   3500.0ms uptime: 100.0%
github-api           DOWN   503   900.0ms  uptime: 0.0%

recent incidents:
  jsonplaceholder 2026-08-26 15:40   slow (3500.0ms)
  github-api      2026-08-26 15:40   got 503
```

An endpoint can carry an optional `latency_threshold_ms` in the config -
a check that passes on status code but takes longer than that shows as
`SLOW` instead of `UP` and lands in recent incidents, without dragging
uptime down (it did respond, just slowly - that's a warning, not a
failure). `check` exits non-zero if anything is actually `DOWN`, so it
can gate a cron job or CI step; a `SLOW` result alone won't fail it.

Both commands take `--config` and `--db` to point at a different config or
history file; `report` also takes `--window` to change how many recent
checks the uptime number and incident list look back over (defaults to
20 - a guess, not a measured number, worth revisiting once this has run
for a while). Every run of `check` appends to `data/history.db` (sqlite,
gitignored), so uptime and incidents build up real history instead of
just reflecting the last check. An existing history.db upgrades itself
in place the first time you run against the new schema - no need to
delete it.

Not installable yet - run it as a module from the repo root, not as a
standalone `watchpost` command. That's the packaging step, still ahead.

## status

Config loader, polling engine, local history, the check/report CLI, and
rule-based alerting (failures plus a latency threshold) are done, with
tests. No webhook or LLM diagnosis yet, and not packaged as an
installable command.
