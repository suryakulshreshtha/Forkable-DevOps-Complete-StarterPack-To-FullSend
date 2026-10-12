"""Request and response shapes. Pydantic validates every field at the API edge."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Environment(StrEnum):
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"


class Status(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


# Outcomes that needed someone to step in. DORA counts these towards change fail rate.
NEEDS_INTERVENTION = frozenset({Status.FAILED, Status.ROLLED_BACK})


class DeploymentIn(BaseModel):
    """What a client sends to record a deployment."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    service: str = Field(
        min_length=1,
        max_length=63,
        pattern=r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$",
        description="Lower-case service name, the same rules as a Kubernetes resource name.",
        examples=["checkout-api"],
    )
    version: str = Field(min_length=1, max_length=64, examples=["1.4.2"])
    environment: Environment
    status: Status = Status.SUCCEEDED
    commit_sha: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{7,40}$",
        description="Short or full Git commit SHA in lower-case hex.",
    )


class StatusUpdate(BaseModel):
    """Change the outcome of a recorded deployment, for example after a rollback."""

    model_config = ConfigDict(extra="forbid")

    status: Status


class Deployment(DeploymentIn):
    """A stored deployment, as the API returns it."""

    id: int
    created_at: datetime


class DoraSnapshot(BaseModel):
    """Delivery metrics for one environment, computed from recorded deployments."""

    deployments: int = Field(description="Deployments recorded in the window.")
    deployment_frequency_per_day: float = Field(description="deployments / window_days")
    needed_intervention: int = Field(description="Deployments that failed or were rolled back.")
    change_fail_rate: float = Field(description="needed_intervention / deployments (0 when none).")
    recovery_time_median_hours: float | None = Field(
        description=(
            "Median time from a failed or rolled-back deployment to the next successful "
            "deployment of the same service. Null when nothing has recovered yet."
        )
    )


class DoraReport(BaseModel):
    window_days: int
    environments: dict[str, DoraSnapshot]


class Info(BaseModel):
    app: str
    version: str
    git_sha: str
    environment: str
