# QA track: testing that earns trust

Quality is not a phase at the end; it is built into every stage of the loop.
This track explains how this repository tests itself, so you can copy the
approach into any project.

## The test pyramid, as built here

```text
                 ▲  few, slow, closest to the user
                ╱ ╲
               ╱E2E╲        tests/e2e        5 Playwright tests in a real Chromium
              ╱─────╲
             ╱  API  ╲      tests/api        HTTP-level tests through FastAPI's TestClient
            ╱─────────╲
           ╱   UNIT    ╲    tests/unit       pure logic: store, config, metrics, logging
          ╱─────────────╲
         ╱ STATIC CHECKS ╲  Ruff · mypy --strict · Bandit · schema validation · repo audit
        ╱─────────────────╲ many, instant, catch whole classes of bugs
```

Plus three kinds of test that are easy to forget:

| Kind | Where | What it protects |
|---|---|---|
| Tests for the tools | `scripts/test_scripts.py`, every `phases/*/check_phase*.py` | Validators, scanners and lab scripts are code too |
| Guardrail tests | `tests/agent/test_server.py`, `phases/04-cicd/check_phase04.py` | Safety rules (writes refused, actions pinned) cannot silently disappear |
| Infrastructure tests | `infra.yml` workflow | The chart renders, the manifests match the Kubernetes API, the app really starts on a cluster |

## Rules this repo follows

| Rule | Example in this repo |
|---|---|
| Test behaviour, not implementation | API tests call endpoints; they do not reach into private functions |
| Control time and randomness | `FakeClock` in `tests/conftest.py`; seeded `random.Random` for chaos tests |
| No network in unit and API tests | GitHub is faked with `httpx.MockTransport` in `tests/agent/fake_github.py` |
| Isolated state | `create_app()` builds a fresh app, store and metrics registry per test |
| Assert on what users see | E2E tests use roles and labels (`get_by_role`, `get_by_label`), never CSS classes |
| No sleeps | Playwright's `expect()` retries until the condition holds or times out |
| A failing test explains itself | Test names read as sentences; assertions say what should be true |
| Coverage is a floor, not a goal | CI fails under 90%, but a test without a meaningful assertion is worse than none |

## Playwright for Python in this repo

| Task | Command (same on macOS and Windows) |
|---|---|
| Install the browser once | `python -m playwright install chromium` |
| Run the browser tests | `python tasks.py e2e` |
| Watch them run | `python tasks.py e2e --headed --slowmo 300` |
| Other browsers | `python tasks.py e2e --browser firefox --browser webkit` (install them first with `python -m playwright install firefox webkit`) |
| Keep a trace when a test fails | `python tasks.py e2e --tracing retain-on-failure` |
| Open a trace | `python -m playwright show-trace test-results/<test>/trace.zip` |
| Record a new test by clicking | start the app (`python tasks.py serve`), then `python -m playwright codegen http://127.0.0.1:8000` |

The `live_server` fixture in `tests/e2e/conftest.py` starts the real app as a
separate process on a free port and waits for `/healthz/ready`, so browser tests
exercise the same code path as production. CI keeps traces and screenshots of
failures as artifacts.

## Flaky tests: what to do

A flaky test passes and fails without code changes. It teaches people to ignore
red builds, which is worse than having no test.

1. **Reproduce:** run it many times in a row (a shell loop around `python -m pytest -k <name>`), alone and with the full suite, and under CPU load.
2. **Classify the cause:** timing (a sleep or a missing wait), shared state between tests, order dependence, real network or clock, randomness without a seed.
3. **Fix the cause,** not the symptom. Retries hide the problem; use them only for genuinely external dependencies, and track them.
4. **Quarantine if you must,** with an issue and an owner, never silently.

## Exercises

1. Add a Playwright test that records a `rolled_back` deployment and checks the amber badge text.
2. Run the E2E suite in Firefox and WebKit. Does anything differ?
3. Write a test that would have caught the chaos-route labelling bug fixed in `src/fullsend/main.py` (`_route_template`). Hint: `test_chaos_failures_are_counted_under_the_real_route` already exists; read it, delete it, and write your own.
4. Make a test flaky on purpose (add a random sleep), observe it, then fix it properly.

## Official docs

- Playwright for Python: <https://playwright.dev/python/docs/intro>
- Locators and assertions: <https://playwright.dev/python/docs/locators> · <https://playwright.dev/python/docs/test-assertions>
- Trace viewer: <https://playwright.dev/python/docs/trace-viewer-intro>
- pytest: <https://docs.pytest.org/en/stable/>
- FastAPI testing: <https://fastapi.tiangolo.com/tutorial/testing/>
- HTTPX mock transport: <https://www.python-httpx.org/advanced/transports/>
