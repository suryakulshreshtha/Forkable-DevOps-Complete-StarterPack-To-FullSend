# Phase 2 · Workflow: Git, pull requests, tests, and working with AI

**Time:** 1–2 weeks · **Roadmap map:** milanm/DevOps-Roadmap steps 1 (Git) and 12 (software engineering practices)

**You finish with:** a clean pull-request habit, commit messages tools can read,
tests you trust, and an AI log that shows you understand what you ship.

## Why hiring teams care

DevOps work is software work: infrastructure, pipelines and tests all live in Git
and change through reviewed pull requests. One 2026 contract SRE posting we read
says the manager wants engineers "already incorporating AI into their daily
development process", and NVIDIA's senior DevOps posting asks for "demonstrated
use of AI tools to improve productivity and the quality of releases". Phase 2 is
where you build that habit, with proof.

---

## 1. Set up Git once

These commands are the same in macOS Terminal and Windows PowerShell.

| Step | Command |
|---|---|
| Your name on commits | `git config --global user.name "Your Name"` |
| Your commit email | `git config --global user.email "ID+USERNAME@users.noreply.github.com"` |
| Default branch name | `git config --global init.defaultBranch main` |
| Turn on this repo's commit-message hook | `git config core.hooksPath phases/02-workflow/hooks` |

Use your **GitHub no-reply address** to keep your real email out of public history:
GitHub → Settings → Emails → "Keep my email addresses private" shows it. For
accounts created after 18 July 2017 it has the form `ID+USERNAME@users.noreply.github.com`
(GitHub docs). Line endings are handled by this repo's `.gitattributes`, so the
same files look identical on macOS and Windows.

## 2. The pull-request loop

```text
main ──●────────────────────●──────▶   always releasable
        \                  /
         ●──●──●  feature  ●           short-lived branch, small change
            │              │
          commits     PR: CI green + review + squash merge
```

| Step | Command |
|---|---|
| Start from fresh main | `git switch main` then `git pull --ff-only` |
| New branch | `git switch -c feat/dora-endpoint` |
| See what changed | `git status` · `git diff` |
| Stage and commit | `git add -p` (review each hunk) then `git commit` |
| Update with main | `git fetch origin` then `git rebase origin/main` |
| Publish | `git push -u origin feat/dora-endpoint` |
| Undo the last commit, keep the changes | `git reset --soft HEAD~1` |
| Find what broke it | `git bisect start`, `git bisect bad`, `git bisect good <sha>` |

**Merge or rebase?** Merging keeps history exactly as it happened and adds a merge
commit. Rebasing replays your commits on top of the latest main for a straight
line. Rebase your **own** unpublished branch freely; never rebase commits other
people already pulled.

**Good pull requests are small.** Aim for a change a reviewer can understand in
fifteen minutes. The [PR template](../../.github/pull_request_template.md) asks how
you checked the change.

## 3. Commit messages tools can read

This repo uses [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/):

```text
feat(api): record rollbacks as a separate status
fix!: reject service names with uppercase letters

Body explains why, wrapped at ~72 characters.
```

| Type | Use for |
|---|---|
| `feat` | a new capability |
| `fix` | a bug fix |
| `docs` · `test` · `ci` · `build` · `refactor` · `perf` · `style` · `chore` | the rest |
| `!` after the type | a breaking change |

The hook you enabled in step 1 runs [`commit_msg_check.py`](commit_msg_check.py)
on every commit. It checks the format, and it also blocks AI credit lines (AI
co-author trailers, tool footers, session links), using the same hashed list as the
[repository audit](../../scripts/repo_audit.py). Git for Windows runs hooks with its
bundled `sh`, so the same hook works on all three systems. Try it:

| Command | Result |
|---|---|
| `git commit --allow-empty -m "did stuff"` | blocked, with the reason |
| `git commit --allow-empty -m "chore: try the commit hook"` | accepted |

## 4. Tests you can trust

Read the [QA track](../../qa/README.md) now; it explains the test pyramid this repo
follows and why the browser tests are few. Then, hands on:

| Do this | Command |
|---|---|
| Run only the fast tests | `python -m pytest tests/unit` |
| Run one test by name | `python -m pytest -k dora` |
| Stop at the first failure, show prints | `python -m pytest -x -s` |
| See what is not covered | `python tasks.py test` (coverage report at the end) |

**Lab: test-first change.** Add a `GET /api/v1/deployments?service=<name>` filter.

1. Write a failing API test in `tests/api/test_api.py` (record two services, filter one).
2. Run it and watch it fail for the right reason.
3. Implement the filter in `src/fullsend/main.py` and `store.py`.
4. `python tasks.py check` must pass. Open a pull request against your fork.

## 5. How teams plan work (SDLC and Scrum in one table)

| Idea | What it means for you |
|---|---|
| SDLC | Plan → code → build → test → release → deploy → operate → monitor, then again. Every phase of this pack covers one part of that loop. |
| Scrum | Work in short sprints; a backlog of small, valuable items; a daily check-in; a review and a retrospective at the end. |
| Definition of done | "Merged" is not done. Done = tested, deployed, observable, documented. |
| Blameless culture | When something breaks, fix the system that allowed it, not the person who triggered it (Phase 6 postmortems). |

## 6. Working with an AI assistant, honestly

Copy [`AI_LOG_TEMPLATE.md`](AI_LOG_TEMPLATE.md) to `AI_LOG.md` and log every
meaningful assist. The DORA 2025 report found that AI amplifies what a team already
does well or badly, and that trust in AI output is still low. Verifying is the job.

| Do | Don't |
|---|---|
| Ask it to explain code, error messages and unfamiliar flags | Paste secrets, tokens, customer data or internal hostnames |
| Ask for tests that try to break your code | Merge code you cannot explain line by line |
| Ask for a review of your diff before a human sees it | Let it run commands that change infrastructure without you reading them |
| Write the commit message and PR description yourself | Add AI credit lines to commits or PRs; they carry your name only |

## Check yourself

```text
python -m pytest phases/02-workflow
```

## Interview questions

1. Explain merge versus rebase. When is rebasing dangerous?
2. A teammate force-pushed to `main` and your history is gone. How do you recover? (Hint: `git reflog`.)
3. How small should a pull request be, and why?
4. What makes a test flaky, and what do you do with one you find?
5. Your team writes more code with AI help, it passes review, but production incidents went up. What would you change?
6. Walk me through how a change gets from your laptop to production in your ideal workflow.

## AI exercise (with guardrails)

Ask an assistant to write the `?service=` filter test from the lab **before** you
write the code. Check that the test fails for the right reason, read every line,
fix what is wrong, and log it. Did it test the empty-result case? Did it reach
into private internals instead of using the API?

## Done when

- [ ] Commits go through the hook; your history follows Conventional Commits
- [ ] The `?service=` filter is merged through a pull request with CI green
- [ ] `AI_LOG.md` has at least three honest entries
- [ ] `python -m pytest phases/02-workflow` passes

## Official docs

- Pro Git book: <https://git-scm.com/book/en/v2>
- `git rebase`, `git reflog`, `git bisect`: <https://git-scm.com/docs/git-rebase> · <https://git-scm.com/docs/git-reflog> · <https://git-scm.com/docs/git-bisect>
- Git hooks and `core.hooksPath`: <https://git-scm.com/docs/githooks>
- GitHub: setting your commit email: <https://docs.github.com/en/account-and-profile/how-tos/email-preferences/setting-your-commit-email-address>
- Conventional Commits 1.0.0: <https://www.conventionalcommits.org/en/v1.0.0/>
- pytest: <https://docs.pytest.org/en/stable/>
- DORA 2025 report announcement: <https://blog.google/technology/developers/dora-report-2025/>

Previous: [Phase 1](../01-foundations/README.md) · Next: [Phase 3 · Containers](../03-containers/README.md)
