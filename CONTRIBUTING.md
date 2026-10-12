# Contributing

Thank you for helping make this pack better for the next learner. Fixes to broken
steps, outdated versions and unclear explanations are the most valuable contributions.

## Before you start

| Step | Command (same on macOS and Windows, virtual environment active) |
|---|---|
| Set up | `python tasks.py setup` (see [Phase 0](phases/00-setup/README.md)) |
| Enable the commit-message hook | `git config core.hooksPath phases/02-workflow/hooks` |
| Branch from fresh main | `git switch main`, `git pull --ff-only`, `git switch -c fix/<short-name>` |

## Rules for changes

| Rule | Why |
|---|---|
| Run `python tasks.py check` (and `python tasks.py e2e` if the app or UI changed) before opening a pull request | CI runs the same checks; save yourself a round trip |
| Every new fact, version or command links to its **official** source in [SOURCES.md](SOURCES.md) or [VERSIONS.md](VERSIONS.md) | Learners must be able to check what they are told |
| Pin exact versions; pin GitHub Actions to a full commit SHA with the version in a comment | Reproducible builds and supply-chain safety (Phase 7) |
| When a command differs between macOS and Windows, show a table for each; when it is the same, one table says so | Learners use both systems |
| Follow the [tool policy](TOOLS.md) | New tools must have an established steward and pass the repository audit |
| Commit messages follow Conventional Commits | The hook checks it; changelogs and history stay readable |
| Commits and pull requests carry **your** name only | No AI co-author trailers, AI-tool footers or session links; `python tasks.py repo-audit` rejects them in files |
| Write lessons in your own words; link other projects instead of copying them | Licences differ, and original explanations teach better |

## Lesson structure

Each phase README keeps the same sections, and `phases/08-capstone/check_phase08.py`
tests for them: **Why hiring teams care**, the lesson and labs, **Check yourself**,
**Interview questions**, **AI exercise (with guardrails)**, **Done when**, and
**Official docs**. Each phase also ships a `check_phase*.py` self-check.

## Reporting problems

Use the issue templates: "Bug or broken lab step" (tell us your OS and versions) or
"Lesson improvement". For security issues, follow [SECURITY.md](SECURITY.md) instead.

## Conduct

Be kind, assume good intent, and review the change, not the person. Blameless
postmortems (Phase 6) apply to this project too.

By contributing, you agree that your contributions are licensed under the
[Apache License 2.0](LICENSE), as section 5 of that licence describes.
