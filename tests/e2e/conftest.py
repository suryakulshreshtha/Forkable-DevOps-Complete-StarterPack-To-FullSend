"""End-to-end fixtures: the real app in its own process, driven by a real browser."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
from collections.abc import Iterator
from typing import Any

import pytest


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_until_ready(url: str, process: subprocess.Popen[bytes], timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"the app exited early with code {process.returncode}")
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:  # noqa: S310 - local test server
                if resp.status == 200:
                    return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"{url} did not answer 200 within {timeout:.0f}s")


@pytest.fixture(scope="session")
def live_server() -> Iterator[str]:
    """Start `python -m fullsend` on a free port, exactly as production starts it."""
    port = _free_port()
    env = {
        **os.environ,
        "HOST": "127.0.0.1",
        "PORT": str(port),
        "APP_ENV": "e2e",
        "LOG_LEVEL": "WARNING",
    }
    process = subprocess.Popen(
        [sys.executable, "-m", "fullsend"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        _wait_until_ready(f"{base_url}/healthz/ready", process, timeout=20)
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args: dict[str, Any]) -> dict[str, Any]:
    """Use a pre-installed Chromium when E2E_CHROMIUM_EXECUTABLE is set.

    Normal setups never need this: `python -m playwright install chromium`
    downloads the browser Playwright expects. It exists for locked-down machines
    that provide their own Chromium build.
    """
    path = os.environ.get("E2E_CHROMIUM_EXECUTABLE")
    if path:
        return {**browser_type_launch_args, "executable_path": path}
    return browser_type_launch_args
