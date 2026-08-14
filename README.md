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

- [ ] YAML config: endpoints to watch, expected status code, timeout, check interval
- [ ] polling engine that hits each endpoint and records status + latency
- [ ] local history (sqlite) so uptime/latency show trends, not just the last check
- [ ] CLI report command - current status and recent incidents per endpoint
- [ ] rule-based alerting when a check fails or latency crosses a threshold
- [ ] optional webhook alert (Slack/Discord) behind a flag
- [ ] optional LLM diagnosis behind a flag - reads a failure (status, body, recent history) and writes a plain-english guess at what went wrong
- [ ] packaging - installable CLI, entry point
- [ ] tests alongside each feature
- [ ] polish pass - license, real verified usage output, known-limitations section

## setup

Nothing to run yet - this is just the scaffold.

## status

Day one. Scaffolding only, no code.
