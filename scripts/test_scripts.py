"""Tests for the repository's own tooling. Tools that guard quality need tests too."""

from __future__ import annotations

import hashlib
import json
import socket
import threading
from collections.abc import Iterator
from pathlib import Path
from wsgiref.simple_server import WSGIRequestHandler, make_server

import pytest

import repo_audit
import smoke_test
import validate_files
import validate_k8s

# ----------------------------------------------------------------- validate_files


def test_validate_files_reports_broken_yaml_and_json(tmp_path: Path) -> None:
    (tmp_path / "good.yaml").write_text("a: 1\n---\nb: 2\n")
    (tmp_path / "bad.yaml").write_text("a: [1, 2\n")
    (tmp_path / "bad.json").write_text("{nope}")
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "helm.yaml").write_text("{{ .Values.x }}: [")  # skipped
    errors = validate_files.check(tmp_path)
    assert len(errors) == 2
    assert any("bad.yaml" in e for e in errors)
    assert any("bad.json" in e for e in errors)


# ----------------------------------------------------------------- validate_k8s (offline)

FAKE_SPEC = {
    "definitions": {
        "io.k8s.api.core.v1.ConfigMap": {
            "type": "object",
            "properties": {
                "apiVersion": {"type": "string"},
                "kind": {"type": "string"},
                "metadata": {"type": "object"},
                "data": {"type": "object", "additionalProperties": {"type": "string"}},
            },
            "x-kubernetes-group-version-kind": [
                {"group": "", "version": "v1", "kind": "ConfigMap"}
            ],
        },
        "io.k8s.apimachinery.pkg.util.intstr.IntOrString": {"type": "string"},
        "io.k8s.apimachinery.pkg.api.resource.Quantity": {"type": "string"},
    }
}


def test_index_by_kind_maps_api_version_and_kind() -> None:
    index = validate_k8s.index_by_kind(FAKE_SPEC["definitions"])
    assert index[("v1", "ConfigMap")] == "io.k8s.api.core.v1.ConfigMap"


def test_strict_definitions_reject_unknown_fields_and_relax_scalars() -> None:
    strict = validate_k8s.strict_definitions(FAKE_SPEC["definitions"])
    assert strict["io.k8s.api.core.v1.ConfigMap"]["additionalProperties"] is False
    assert strict["io.k8s.apimachinery.pkg.util.intstr.IntOrString"]["type"] == [
        "integer",
        "string",
    ]
    # The original spec is untouched.
    assert "additionalProperties" not in FAKE_SPEC["definitions"]["io.k8s.api.core.v1.ConfigMap"]


def test_validate_uses_the_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(validate_k8s, "load_spec", lambda: FAKE_SPEC)
    (tmp_path / "ok.yaml").write_text("apiVersion: v1\nkind: ConfigMap\nmetadata: {name: a}\n")
    (tmp_path / "typo.yaml").write_text("apiVersion: v1\nkind: ConfigMap\ndatta: {}\n")
    (tmp_path / "crd.yaml").write_text("apiVersion: example.com/v1\nkind: Widget\n")
    (tmp_path / "kustomization.yaml").write_text(
        "apiVersion: kustomize.config.k8s.io/v1beta1\nkind: Kustomization\n"
    )
    checked, skipped, errors = validate_k8s.validate([str(tmp_path)])
    assert (checked, skipped) == (2, 2)
    assert len(errors) == 1
    assert "datta" in errors[0]


# ----------------------------------------------------------------- repo_audit


def test_denied_terms_are_found_by_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    probe = "forbiddenprobe"
    monkeypatch.setitem(
        repo_audit.DENIED, "test", frozenset({hashlib.sha256(probe.encode()).hexdigest()})
    )
    monkeypatch.setattr(repo_audit, "ROOT", tmp_path)
    target = tmp_path / "doc.md"
    target.write_text(f"line one\nthis mentions {probe.upper()} here\n")
    problems = repo_audit.denied_terms(target)
    assert problems == [f"doc.md:2: test (hash {hashlib.sha256(probe.encode()).hexdigest()[:10]})"]


def test_word_pairs_are_checked_too(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pair = "alpha beta"
    monkeypatch.setitem(
        repo_audit.DENIED, "pair", frozenset({hashlib.sha256(pair.encode()).hexdigest()})
    )
    monkeypatch.setattr(repo_audit, "ROOT", tmp_path)
    target = tmp_path / "a.md"
    target.write_text("Alpha Beta\n")
    assert len(repo_audit.denied_terms(target)) == 1


def test_broken_internal_links_are_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(repo_audit, "ROOT", tmp_path)
    (tmp_path / "exists.md").write_text("# hi\n")
    doc = tmp_path / "README.md"
    doc.write_text("[ok](exists.md) [anchor](#x) [web](https://example.org) [bad](missing.md#y)\n")
    assert repo_audit.broken_internal_links(doc) == ["README.md: broken link -> missing.md#y"]


def test_this_repository_passes_its_own_audit() -> None:
    assert repo_audit.main([]) == 0


# ----------------------------------------------------------------- smoke_test


def _fake_app(environ: dict[str, object], start_response: object) -> list[bytes]:
    path = str(environ["PATH_INFO"])
    method = str(environ["REQUEST_METHOD"])
    status = "201 Created" if method == "POST" else "200 OK"
    if path == "/api/v1/info" and FakeState.broken:
        status = "500 Internal Server Error"
    start_response(status, [("Content-Type", "application/json")])  # type: ignore[operator]
    return [json.dumps({"path": path}).encode()]


class FakeState:
    broken = False


class _Quiet(WSGIRequestHandler):
    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def fake_server() -> Iterator[str]:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = make_server("127.0.0.1", port, _fake_app, handler_class=_Quiet)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
    server.server_close()


def test_smoke_test_passes_against_a_healthy_service(fake_server: str) -> None:
    FakeState.broken = False
    assert smoke_test.run(fake_server, timeout=5) == []


def test_smoke_test_reports_a_failing_check(fake_server: str) -> None:
    FakeState.broken = True
    failures = smoke_test.run(fake_server, timeout=5)
    assert len(failures) == 1
    assert failures[0].startswith("info: expected 200, got 500")


def test_smoke_test_gives_up_when_nothing_answers() -> None:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    failures = smoke_test.run(f"http://127.0.0.1:{port}", timeout=1)
    assert len(failures) == 1
    assert "did not answer 200" in failures[0]
