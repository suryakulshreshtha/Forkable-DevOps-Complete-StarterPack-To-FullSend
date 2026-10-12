"""Entry point: ``python -m fullsend`` (also installed as the ``fullsend`` command)."""

from __future__ import annotations

import uvicorn

from fullsend.config import Settings


def main() -> None:
    settings = Settings.from_env()
    uvicorn.run(
        "fullsend.main:app",
        host=settings.host,
        port=settings.port,
        log_config=None,  # the app writes its own JSON logs
        access_log=False,  # the app writes its own access log with request ids
        timeout_graceful_shutdown=20,  # finish in-flight requests when Kubernetes sends SIGTERM
    )


if __name__ == "__main__":
    main()
