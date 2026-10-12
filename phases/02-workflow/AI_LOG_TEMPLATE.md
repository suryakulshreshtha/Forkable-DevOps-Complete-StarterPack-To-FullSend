# AI log

Keep one entry per meaningful use of an AI assistant. The point is not paperwork:
it is how you prove (to yourself and to an interviewer) that you understand the
code you ship, and how you spot where assistants help and where they mislead you.

Copy this file to `AI_LOG.md` at the repository root and commit it if you are comfortable sharing it.

| Date | Task | What I asked | What it got right | What it got wrong or I had to fix | How I verified | Time saved or lost |
|---|---|---|---|---|---|---|
| 2026-10-12 | Example: write log_report percentile | "nearest-rank percentile in Python, no numpy" | Correct algorithm | Off-by-one for p100 | Wrote a test with [1,2,3,4] | ~10 min saved |

## Rules I follow

1. I never paste secrets, tokens, customer data or internal hostnames into an external assistant.
2. I do not merge code I cannot explain line by line.
3. Every AI suggestion that changes behaviour gets a test.
4. Commands that change infrastructure are read by me before they run, every time.
5. Commit messages and pull requests are written in my own words and carry only my name.
