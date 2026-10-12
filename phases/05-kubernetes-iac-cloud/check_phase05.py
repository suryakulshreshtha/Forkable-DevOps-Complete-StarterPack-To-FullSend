"""Self-check for Phase 5. Run: python -m pytest phases/05-kubernetes-iac-cloud"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
import rollout_report
import tf_plan_guard
import yaml

ROOT = Path(__file__).resolve().parents[2]


def deployment(
    name: str, desired: int, ready: int, updated: int, reason: str = ""
) -> dict[str, Any]:
    conditions = [{"type": "Progressing", "reason": reason or "NewReplicaSetAvailable"}]
    return {
        "metadata": {"namespace": "fullsend", "name": name},
        "spec": {"replicas": desired},
        "status": {"readyReplicas": ready, "updatedReplicas": updated, "conditions": conditions},
    }


# ------------------------------------------------------------------ rollout_report


def test_healthy_rollout() -> None:
    assert rollout_report.assess(deployment("api", 2, 2, 2)).healthy


@pytest.mark.parametrize(
    ("item", "fragment"),
    [
        (deployment("api", 3, 3, 3, "ProgressDeadlineExceeded"), "stuck"),
        (deployment("api", 3, 2, 1), "1/3 pods on the new version"),
        (deployment("api", 3, 1, 3), "only 1/3 pods ready"),
    ],
)
def test_unhealthy_rollouts_explain_themselves(item: dict[str, Any], fragment: str) -> None:
    result = rollout_report.assess(item)
    assert not result.healthy
    assert fragment in result.problem


def test_rollout_cli(tmp_path: Path) -> None:
    path = tmp_path / "d.json"
    path.write_text(json.dumps({"items": [deployment("a", 1, 1, 1), deployment("b", 2, 0, 2)]}))
    assert rollout_report.main([str(path)]) == 1


# ------------------------------------------------------------------ tf_plan_guard


def change(address: str, rtype: str, actions: list[str]) -> dict[str, Any]:
    return {"address": address, "type": rtype, "change": {"actions": actions}}


def plan(*changes: dict[str, Any]) -> dict[str, Any]:
    return {"format_version": "1.2", "resource_changes": list(changes)}


def test_additive_plan_is_safe() -> None:
    verdict = tf_plan_guard.evaluate(
        plan(
            change("aws_iam_role.a", "aws_iam_role", ["create"]),
            change("aws_s3_bucket.b", "aws_s3_bucket", ["update"]),
            change("aws_vpc.c", "aws_vpc", ["no-op"]),
        )
    )
    assert verdict.safe
    assert verdict.counts == {"create": 1, "update": 1, "no-op": 1}


@pytest.mark.parametrize("actions", [["delete"], ["delete", "create"], ["create", "delete"]])
def test_every_kind_of_deletion_is_caught(actions: list[str]) -> None:
    verdict = tf_plan_guard.evaluate(plan(change("aws_iam_role.a", "aws_iam_role", actions)))
    assert not verdict.safe


def test_allow_destroy_never_covers_critical_resources(tmp_path: Path) -> None:
    normal = tmp_path / "normal.json"
    normal.write_text(json.dumps(plan(change("aws_iam_role.a", "aws_iam_role", ["delete"]))))
    critical = tmp_path / "critical.json"
    critical.write_text(
        json.dumps(
            plan(
                change(
                    "module.eks.aws_eks_cluster.this[0]", "aws_eks_cluster", ["delete", "create"]
                )
            )
        )
    )
    assert tf_plan_guard.main([str(normal)]) == 1
    assert tf_plan_guard.main([str(normal), "--allow-destroy"]) == 0
    assert tf_plan_guard.main([str(critical), "--allow-destroy"]) == 1


# ------------------------------------------------------------------ the manifests in this repo


def _docs(folder: str) -> list[dict[str, Any]]:
    docs = []
    for path in sorted((ROOT / folder).glob("*.yaml")):
        docs += [d for d in yaml.safe_load_all(path.read_text(encoding="utf-8")) if d]
    return docs


def test_deployment_is_production_shaped() -> None:
    dep = next(d for d in _docs("infra/k8s") if d["kind"] == "Deployment")
    pod = dep["spec"]["template"]["spec"]
    container = pod["containers"][0]
    assert dep["spec"]["replicas"] >= 2, "one replica means downtime on every rollout"
    assert dep["spec"]["strategy"]["rollingUpdate"]["maxUnavailable"] == 0
    assert pod["securityContext"]["runAsNonRoot"] is True
    assert container["securityContext"]["allowPrivilegeEscalation"] is False
    assert container["securityContext"]["readOnlyRootFilesystem"] is True
    assert {"readinessProbe", "livenessProbe", "startupProbe"} <= set(container)
    assert "requests" in container["resources"]
    assert "memory" in container["resources"]["limits"]


def test_namespace_enforces_restricted_pod_security() -> None:
    ns = next(d for d in _docs("infra/k8s") if d["kind"] == "Namespace")
    assert ns["metadata"]["labels"]["pod-security.kubernetes.io/enforce"] == "restricted"


def test_kind_node_image_is_pinned_by_digest() -> None:
    config = yaml.safe_load((ROOT / "infra/kind/kind-config.yaml").read_text(encoding="utf-8"))
    for node in config["nodes"]:
        assert re.search(r"@sha256:[0-9a-f]{64}$", node["image"])


def test_terraform_modules_are_pinned_to_exact_versions() -> None:
    main_tf = (ROOT / "infra/terraform/aws-eks/main.tf").read_text(encoding="utf-8")
    versions = re.findall(r'version\s*=\s*"([^"]+)"', main_tf)
    assert versions
    assert all(re.fullmatch(r"\d+\.\d+\.\d+", v) for v in versions)


def test_terraform_state_and_variables_are_gitignored() -> None:
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "*.tfstate" in ignore
    assert "*.tfvars" in ignore
