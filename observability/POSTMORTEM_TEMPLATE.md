# Postmortem: <short title>

**Blameless:** this document is about how our systems and processes allowed the
problem, not about who pressed which button. People acted on the information
they had at the time.

| | |
|---|---|
| Date | YYYY-MM-DD |
| Authors | |
| Status | Draft / Reviewed / Actions complete |
| Severity | Page / Ticket |
| Duration | from first user impact to full recovery |
| Error budget spent | e.g. 18% of the 30-day budget (from Grafana or `slo_calc.py`) |

## Summary

Two or three sentences a busy reader can stop after.

## User impact

What users saw, how many, for how long.

## Timeline (UTC)

| Time | Event |
|---|---|
| 10:02 | Release v1.4.0 deployed |
| 10:09 | FullSendErrorBudgetFastBurn fired |
| 10:12 | On-call acknowledged, started investigating |
| 10:20 | Rolled back; errors back to normal |

## Root cause and trigger

The **trigger** is what started it (a deploy, a config change). The **root cause**
is why the system could not tolerate it. Ask "why?" until you reach something you can change.

## What went well · What went badly · Where we got lucky

-
-
-

## Action items

| Action | Type (prevent / detect / mitigate) | Owner | Due | Ticket |
|---|---|---|---|---|
| | | | | |

## Lessons

What would you tell another team so they avoid this?
