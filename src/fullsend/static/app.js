// FullSend Deploy Log: a tiny, dependency-free front end.
// It talks only to this app's own API (enforced by the Content-Security-Policy).
"use strict";

const api = {
  list: () => fetch("/api/v1/deployments?limit=50").then(checked),
  dora: () => fetch("/api/v1/dora?window_days=30").then(checked),
  create: (body) =>
    fetch("/api/v1/deployments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(checked),
};

async function checked(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((d) => `${d.loc.at(-1)}: ${d.msg}`).join("; ")
      : data.detail || `HTTP ${response.status}`;
    throw new Error(detail);
  }
  return data;
}

function percent(rate) {
  return `${(rate * 100).toFixed(1).replace(/\.0$/, "")}%`;
}

function cell(text, className) {
  const td = document.createElement("td");
  td.textContent = text; // textContent, never innerHTML: user input is never parsed as HTML
  if (className) td.className = className;
  return td;
}

function renderRows(items) {
  const body = document.getElementById("deployments");
  body.replaceChildren(
    ...items.map((d) => {
      const tr = document.createElement("tr");
      tr.append(
        cell(String(d.id)),
        cell(d.service),
        cell(d.version),
        cell(d.environment),
        cell(d.status, `badge badge-${d.status}`),
        cell(d.commit_sha || "-"),
        cell(new Date(d.created_at).toISOString().replace("T", " ").slice(0, 19)),
      );
      return tr;
    }),
  );
  document.getElementById("empty").hidden = items.length > 0;
}

function hours(value) {
  if (value === null || value === undefined) return "n/a";
  return value < 1 ? `${Math.round(value * 60)} min` : `${value.toFixed(1).replace(/\.0$/, "")} h`;
}

function renderStats(report) {
  const envs = Object.values(report.environments);
  const total = envs.reduce((sum, e) => sum + e.deployments, 0);
  const prod = report.environments.production;
  document.querySelector('[data-stat="total"]').textContent = String(total);
  document.querySelector('[data-stat="production-cfr"]').textContent = percent(prod.change_fail_rate);
  document.querySelector('[data-stat="production-recovery"]').textContent = hours(
    prod.recovery_time_median_hours,
  );
}

async function refresh() {
  const [items, report] = await Promise.all([api.list(), api.dora()]);
  renderRows(items);
  renderStats(report);
}

function formPayload(form) {
  const data = Object.fromEntries(new FormData(form).entries());
  const payload = {
    service: data.service.trim(),
    version: data.version.trim(),
    environment: data.environment,
    status: data.status,
  };
  const sha = data.commit_sha.trim();
  if (sha) payload.commit_sha = sha;
  return payload;
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("deploy-form");
  const statusEl = document.getElementById("form-status");
  const errorEl = document.getElementById("form-error");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    statusEl.textContent = "";
    errorEl.textContent = "";
    const payload = formPayload(form);
    if (!payload.service || !payload.version) {
      errorEl.textContent = "Service and version are required.";
      return;
    }
    try {
      const created = await api.create(payload);
      statusEl.textContent = `Recorded deployment #${created.id} (${created.service} ${created.version}).`;
      form.reset();
      await refresh();
    } catch (err) {
      errorEl.textContent = `Could not record deployment: ${err.message}`;
    }
  });

  refresh().catch((err) => {
    errorEl.textContent = `Could not load data: ${err.message}`;
  });
});
