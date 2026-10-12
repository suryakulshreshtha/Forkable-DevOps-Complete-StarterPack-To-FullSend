"""Self-check for Phase 6. Run: python -m pytest phases/06-reliability"""

from __future__ import annotations

import random
import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import load_gen
import pytest
import slo_calc
import uvicorn
import yaml

from fullsend.config import Settings
from fullsend.main import create_app

ROOT = Path(__file__).resolve().parents[2]
RULES = yaml.safe_load((ROOT / "observability/prometheus/rules.yml").read_text(encoding="utf-8"))

# ------------------------------------------------------------------ the maths


@pytest.mark.parametrize(
    ("slo", "budget", "minutes_30d"),
    [(99.0, 0.01, 432.0), (99.9, 0.001, 43.2), (99.99, 0.0001, 4.32)],
)
def test_error_budget_and_downtime(slo: float, budget: float, minutes_30d: float) -> None:
    assert slo_calc.error_budget(slo) == pytest.approx(budget)
    assert slo_calc.allowed_downtime_minutes(slo, 30) == pytest.approx(minutes_30d)


def test_workbook_table_reproduces_its_budget_percentages() -> None:
    # Table 5-8 of the SRE Workbook: 2%, 5% and 10% of a 30-day budget.
    used = [
        slo_calc.budget_consumed(rate, long_h, 30)
        for _, long_h, _, rate in slo_calc.WORKBOOK_ALERTS
    ]
    assert used == pytest.approx([0.02, 0.05, 0.10])


def test_burn_rate_and_exhaustion() -> None:
    rate = slo_calc.burn_rate(0.02, 99.0)  # 2% errors against a 1% budget
    assert rate == pytest.approx(2.0)
    assert slo_calc.days_to_exhaustion(rate, 30) == pytest.approx(15.0)
    assert slo_calc.days_to_exhaustion(0, 30) == float("inf")


def test_invalid_slo_is_rejected() -> None:
    with pytest.raises(ValueError, match="between 0 and 100"):
        slo_calc.error_budget(100)


# ------------------------------------------------------------------ the alert rules match the maths


def _rule(name: str) -> dict[str, object]:
    return next(
        r
        for g in RULES["groups"]
        for r in g["rules"]
        if r.get("alert") == name or r.get("record") == name
    )


def test_fast_burn_alert_uses_workbook_thresholds_for_a_99_percent_slo() -> None:
    expr = str(_rule("FullSendErrorBudgetFastBurn")["expr"])
    assert "(14.4 * 0.01)" in expr
    assert "(6 * 0.01)" in expr
    for window in ("rate1h", "rate5m", "rate6h", "rate30m"):
        assert window in expr


def test_every_alert_has_a_runbook_section_that_exists() -> None:
    runbook = (ROOT / "observability/RUNBOOK.md").read_text(encoding="utf-8").lower()
    alerts = [r for g in RULES["groups"] for r in g["rules"] if "alert" in r]
    assert alerts
    for alert in alerts:
        anchor = str(alert["annotations"]["runbook"]).split("#", 1)[1]
        assert f"## {anchor}" in runbook.replace("`", ""), anchor


def test_sli_only_counts_api_routes() -> None:
    assert 'route=~"/api/.*"' in str(_rule("fullsend:api_error_ratio:rate5m")["expr"])


# ------------------------------------------------------------------ load generator, end to end


@pytest.fixture
def chaotic_server() -> Iterator[str]:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    app = create_app(settings=Settings(chaos_error_rate=0.5), rng=random.Random(3))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


def test_load_generator_sees_injected_failures(chaotic_server: str) -> None:
    results = load_gen.run(chaotic_server, seconds=1.0, workers=2, seed=1)
    total = sum(results.statuses.values())
    failures = results.statuses[503]
    assert total > 20
    assert 0.3 < failures / total < 0.7
