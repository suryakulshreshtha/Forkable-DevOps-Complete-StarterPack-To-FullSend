# Guardrails for AI tools in operations

These rules shape the CI triage server and are worth applying to any AI tool that
touches production systems. Each one answers a concrete way things go wrong.

| # | Rule | What goes wrong without it | How the triage server applies it |
|---|---|---|---|
| 1 | **Read by default, write by exception** | An assistant "helpfully" changes a system while exploring | Three of four tools only read; they carry `read_only_hint` so clients can treat them differently |
| 2 | **Two keys for every write** | One mistaken call, or one manipulated prompt, causes damage | `open_issue` needs a server-side switch a human sets (`CI_TRIAGE_ALLOW_WRITES=1`) **and** `confirm=true` in the call |
| 3 | **Least-privilege credentials** | A leaked or misused token can do far more than the task needs | A fine-grained token with "Actions: read" covers all read tools; "Issues: write" only if writes are enabled |
| 4 | **Untrusted input is data, never instructions** | Text in logs, PR titles or issue comments steers the agent (prompt injection) | Logs come back as evidence in structured fields; no tool acts on log content; the only write needs a human |
| 5 | **Redact before returning** | Secrets printed in CI logs flow into an AI provider's context | Token shapes, AWS key IDs, private keys, bearer headers and `password=`-style pairs are masked |
| 6 | **Bounded output** | Huge logs exhaust context, cost money and bury the real error | Newest 400 KB of each log; at most 40 evidence lines per failed job |
| 7 | **Validate every argument** | Path tricks or malformed input reach the API | `owner/name` must match a strict pattern; `limit` is bounded; checked before any request |
| 8 | **Fail clean** | Stack traces leak internals and confuse the model | HTTP errors become one-line tool errors with a hint about the token |
| 9 | **Test the guardrails, not only the features** | A refactor silently removes a safety check | `tests/agent/test_server.py` asserts that writes are refused and that nothing is POSTed |
| 10 | **A human owns the outcome** | Nobody checks what the agent concluded | The draft is shown to a person; categories are labelled as rule-based guesses |

## Questions to ask before connecting any AI tool to your systems

1. What is the most damaging thing it can do with the credentials it has?
2. Which inputs could someone outside the team write (PR titles, issue text, logs, web pages)?
3. Where does the data it reads go, and is that allowed for this data?
4. How will you notice when it is wrong?
5. Can you switch it off in one step?
