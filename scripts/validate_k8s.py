#!/usr/bin/env python3
"""Validate Kubernetes manifests against the official Kubernetes OpenAPI schema.

No cluster and no third-party validator are needed. The schema is the
`api/openapi-spec/swagger.json` file published in the kubernetes/kubernetes
repository for the version pinned below. It is downloaded once and cached in
.cache/.

Strict mode (the default) also rejects unknown fields, so a typo such as
`replica: 3` instead of `replicas: 3` fails here instead of being silently
ignored by an older cluster.

Usage:
  python scripts/validate_k8s.py infra/k8s            # validate a folder
  python scripts/validate_k8s.py - < rendered.yaml    # validate stdin (e.g. helm template output)
"""

from __future__ import annotations

import copy
import json
import sys
import urllib.request
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft4Validator

KUBERNETES_VERSION = "v1.37.1"
SPEC_URL = (
    "https://raw.githubusercontent.com/kubernetes/kubernetes/"
    f"{KUBERNETES_VERSION}/api/openapi-spec/swagger.json"
)
CACHE = Path(__file__).resolve().parent.parent / ".cache" / f"k8s-swagger-{KUBERNETES_VERSION}.json"

# Kinds that are not Kubernetes API objects (tool configuration files).
NON_API_GROUPS = ("kustomize.config.k8s.io/", "kind.x-k8s.io/")


def load_spec() -> dict[str, Any]:
    if not CACHE.exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        print(f"downloading Kubernetes {KUBERNETES_VERSION} OpenAPI schema …")
        with urllib.request.urlopen(SPEC_URL, timeout=60) as res:  # nosec B310  # fixed https URL
            CACHE.write_bytes(res.read())
    spec: dict[str, Any] = json.loads(CACHE.read_text(encoding="utf-8"))
    return spec


def strict_definitions(definitions: dict[str, Any]) -> dict[str, Any]:
    """Return a copy where objects with declared properties reject unknown fields,
    and the two 'flexible' Kubernetes scalar types accept both forms they allow."""
    defs = copy.deepcopy(definitions)
    for schema in defs.values():
        if schema.get("type") == "object" and "properties" in schema:
            schema.setdefault("additionalProperties", False)
    # IntOrString (ports, maxSurge) and Quantity (cpu: 1 or "500m") accept ints and strings.
    defs["io.k8s.apimachinery.pkg.util.intstr.IntOrString"] = {"type": ["integer", "string"]}
    defs["io.k8s.apimachinery.pkg.api.resource.Quantity"] = {"type": ["number", "string"]}
    return defs


def index_by_kind(definitions: dict[str, Any]) -> dict[tuple[str, str], str]:
    index: dict[tuple[str, str], str] = {}
    for name, schema in definitions.items():
        for gvk in schema.get("x-kubernetes-group-version-kind", []):
            group, version, kind = gvk.get("group", ""), gvk["version"], gvk["kind"]
            api_version = f"{group}/{version}" if group else version
            index[(api_version, kind)] = name
    return index


def documents(paths: Iterable[Path]) -> Iterable[tuple[str, dict[str, Any]]]:
    for path in paths:
        text = sys.stdin.read() if str(path) == "-" else path.read_text(encoding="utf-8")
        for i, doc in enumerate(yaml.safe_load_all(text)):
            if isinstance(doc, dict):
                yield f"{path}#{i}", doc


def collect(targets: list[str]) -> list[Path]:
    paths: list[Path] = []
    for target in targets:
        p = Path(target)
        if target == "-":
            paths.append(p)
        elif p.is_dir():
            paths.extend(sorted(list(p.rglob("*.yaml")) + list(p.rglob("*.yml"))))
        else:
            paths.append(p)
    return paths


def validate(targets: list[str], strict: bool = True) -> tuple[int, int, list[str]]:
    spec = load_spec()
    definitions = strict_definitions(spec["definitions"]) if strict else spec["definitions"]
    index = index_by_kind(spec["definitions"])
    checked = skipped = 0
    errors: list[str] = []
    for where, doc in documents(collect(targets)):
        api_version, kind = doc.get("apiVersion", ""), doc.get("kind", "")
        if api_version.startswith(NON_API_GROUPS):
            skipped += 1
            continue
        name = index.get((api_version, kind))
        if name is None:
            print(f"- skip {where}: {api_version} {kind} is not a built-in kind (a CRD?)")
            skipped += 1
            continue
        schema = {"$ref": f"#/definitions/{name}", "definitions": definitions}
        found = sorted(Draft4Validator(schema).iter_errors(doc), key=lambda e: list(e.path))
        for err in found:
            location = ".".join(str(p) for p in err.path) or "(root)"
            errors.append(f"{where} {kind}: {location}: {err.message}")
        checked += 1
    return checked, skipped, errors


def main(argv: list[str]) -> int:
    strict = "--loose" not in argv
    targets = [a for a in argv if a != "--loose"] or ["infra/k8s"]
    checked, skipped, errors = validate(targets, strict=strict)
    for e in errors:
        print(f"✗ {e}")
    mode = "strict" if strict else "loose"
    print(
        f"Kubernetes {KUBERNETES_VERSION} schema ({mode}): {checked} object(s) checked, "
        f"{skipped} skipped, {len(errors)} error(s)"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
