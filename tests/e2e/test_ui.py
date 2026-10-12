"""Browser tests with Playwright. They check what a user sees, not implementation details.

Good habits shown here (from the Playwright docs):
- find elements the way a person would: by role, label or text;
- use `expect(...)` assertions, which retry until they pass or time out,
  instead of sleeping for a fixed time;
- keep tests independent: each one makes the data it needs.
"""

from __future__ import annotations

import re
import uuid

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def unique_service() -> str:
    return f"svc-{uuid.uuid4().hex[:8]}"


def test_page_loads_with_title_and_sections(page: Page, live_server: str) -> None:
    page.goto(live_server)
    expect(page).to_have_title("FullSend Deploy Log")
    expect(page.get_by_role("heading", name="FullSend Deploy Log")).to_be_visible()
    expect(page.get_by_role("heading", name="Record a deployment")).to_be_visible()
    expect(page.get_by_role("table")).to_be_visible()


def test_record_deployment_shows_in_table(page: Page, live_server: str) -> None:
    service = unique_service()
    page.goto(live_server)
    page.get_by_label("Service").fill(service)
    page.get_by_label("Version").fill("2.0.1")
    page.get_by_label("Environment").select_option("staging")
    page.get_by_role("button", name="Record deployment").click()

    expect(page.get_by_role("status")).to_contain_text(f"{service} 2.0.1")
    row = page.get_by_role("row").filter(has_text=service)
    expect(row).to_have_count(1)
    expect(row).to_contain_text("staging")
    expect(row).to_contain_text("succeeded")


def test_failure_then_fix_updates_production_metrics(page: Page, live_server: str) -> None:
    service = unique_service()
    page.goto(live_server)
    for outcome in ("failed", "succeeded"):  # a failed deploy, then the fix
        page.get_by_label("Service").fill(service)
        page.get_by_label("Version").fill("3.0.0")
        page.get_by_label("Environment").select_option("production")
        page.get_by_label("Outcome").select_option(outcome)
        page.get_by_role("button", name="Record deployment").click()
        expect(
            page.get_by_role("row").filter(has_text=outcome).filter(has_text=service)
        ).to_have_count(1)

    expect(page.locator('[data-stat="production-cfr"]')).to_have_text(re.compile(r"^\d+(\.\d)?%$"))
    expect(page.locator('[data-stat="production-cfr"]')).not_to_have_text("0%")
    # The fix came moments after the failure, so recovery time shows in minutes.
    expect(page.locator('[data-stat="production-recovery"]')).to_have_text(re.compile(r"^\d+ min$"))


def test_server_validation_error_is_shown(page: Page, live_server: str) -> None:
    page.goto(live_server)
    page.get_by_label("Service").fill("Not Valid!")  # the API rejects capitals and spaces
    page.get_by_label("Version").fill("1.0.0")
    page.get_by_role("button", name="Record deployment").click()
    expect(page.get_by_role("alert")).to_contain_text("Could not record deployment")


def test_required_fields_checked_before_sending(page: Page, live_server: str) -> None:
    page.goto(live_server)
    requests: list[str] = []
    page.on("request", lambda r: requests.append(r.url) if r.method == "POST" else None)
    page.get_by_role("button", name="Record deployment").click()
    expect(page.get_by_role("alert")).to_have_text("Service and version are required.")
    assert requests == []
