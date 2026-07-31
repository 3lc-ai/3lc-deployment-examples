# =============================================================================
# <copyright>
# Copyright (c) 2026 3LC Inc. All rights reserved.
#
# All rights are reserved. Reproduction or transmission in whole or in part, in
# any form or by any means, electronic, mechanical or otherwise, is prohibited
# without the prior written permission of the copyright owner.
# </copyright>
# =============================================================================
"""Fixtures for exercising the deployment examples end to end.

Each test module declares a ``TOPOLOGY`` and receives a live ``Stack``: the
``stack`` fixture brings the corresponding Docker Compose deployment up, waits
for every component to answer, and tears it down afterwards. Which surface it
brings up comes from the ``surface`` fixture that each ``tests/<surface>/``
directory defines.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest
import requests

from tests.deployments import (
    HEALTH_PATHS,
    OVERLAYS,
    REPO_ROOT,
    REQUIRED_ENV,
    SURFACES,
    URLS,
    VALUES_OVERLAYS,
    Stack,
)

KUBE_CONTEXT = "docker-desktop"
NAMESPACE = "tlc-demo"
HELM_RELEASE = "tlc-demo"

# The Helm value each .env variable is passed as. The PyPI keys are absent
# on purpose: they are build-time only and never reach the chart.
HELM_VALUE_FOR = {
    "TLC_API_KEY": "global.apiKey",
    "TLC_LICENSE": "global.licenseKey",
    "TLC_OBJECT_SERVICE_AUTH_SECRET": "global.objectServiceAuthSecret",
}


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--keep-stack",
        action="store_true",
        default=False,
        help="leave the deployment running after the tests, for debugging",
    )


@pytest.fixture(scope="session", autouse=True)
def _resolve_dot_localhost() -> None:
    """Point ``*.localhost`` at 127.0.0.1 for the duration of the session.

    Browsers resolve these names themselves (RFC 6761) but the operating system
    resolver does not, so ``requests`` cannot reach the per-host TLS deployment
    without help. Redirecting address resolution leaves the URL, the SNI name,
    the Host header and certificate validation untouched, which is what makes
    this safe: the test still proves the certificate covers the name.
    """
    real_getaddrinfo = socket.getaddrinfo

    def getaddrinfo(host, port, *args, **kwargs):
        if isinstance(host, str) and host.endswith(".localhost"):
            host = "127.0.0.1"
        return real_getaddrinfo(host, port, *args, **kwargs)

    socket.getaddrinfo = getaddrinfo


def _compose(surface_dir: Path, topology: str, *args: str) -> list[str]:
    cmd = ["docker", "compose", "-f", "docker-compose.yml"]
    overlay = OVERLAYS[topology]
    if overlay:
        cmd += ["-f", overlay]
    return cmd + list(args)


def _run(cmd: list[str], cwd: Path, timeout: int = 1800) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False)


def _down_everything() -> None:
    """Stop every example deployment before starting one.

    Both surfaces publish the same host ports (8080, 5001, 5002 for Compose,
    30000 for a Kubernetes NodePort), and all four HTTPS deployments bind 443,
    so only one deployment can run at a time whichever platform it is on.
    Tearing down only the one about to be replaced would leave another holding
    the ports. ``down`` acts on the whole Compose project, so the base file
    alone is enough regardless of which overlay brought it up.
    """
    for surface in SURFACES:
        surface_dir = REPO_ROOT / surface
        _run(
            ["docker", "compose", "-f", "docker-compose.yml", "down", "--remove-orphans"],
            surface_dir,
            timeout=300,
        )
    _helm_uninstall()


def _helm_uninstall() -> None:
    """Remove the Helm release and its namespace, ignoring absence."""
    if not shutil.which("helm"):
        return
    _run(["helm", "uninstall", HELM_RELEASE, "--kube-context", KUBE_CONTEXT, "-n", NAMESPACE], REPO_ROOT, timeout=300)
    _run(
        ["kubectl", "--context", KUBE_CONTEXT, "delete", "namespace", NAMESPACE, "--ignore-not-found"],
        REPO_ROOT,
        timeout=300,
    )


def _require_kubernetes() -> None:
    """Skip unless the tooling and the cluster the examples assume are present."""
    for tool in ("helm", "kubectl"):
        if not shutil.which(tool):
            pytest.skip(f"{tool} is not on PATH")
    nodes = _run(["kubectl", "--context", KUBE_CONTEXT, "get", "nodes", "--no-headers"], REPO_ROOT, timeout=60)
    if nodes.returncode != 0:
        pytest.skip(f"no reachable '{KUBE_CONTEXT}' cluster: {nodes.stderr.strip()[:120]}")
    # The examples need the Kubeadm provisioner, whose node is named
    # docker-desktop. A kind cluster cannot see locally built images.
    if KUBE_CONTEXT not in nodes.stdout:
        pytest.skip(f"cluster is not Kubeadm-provisioned (nodes: {nodes.stdout.split()[:1]})")


def _helm_deploy(surface: str, surface_dir: Path, topology: str) -> None:
    """Deploy with Helm, the way the surface README documents.

    The chart never builds images, so Compose has to have built them first; the
    docker-desktop overlay sets ``imagePullPolicy: Never`` and the pods would
    fail with ``ErrImageNeverPull`` otherwise.
    """
    build = _run(_compose(surface_dir, "http", "build"), surface_dir)
    if build.returncode != 0:
        pytest.fail(f"{surface}: building the images failed:\n{build.stdout}\n{build.stderr}")

    cmd = [
        "helm", "upgrade", "-i", HELM_RELEASE, "./helm",
        "--kube-context", KUBE_CONTEXT,
        "--namespace", NAMESPACE, "--create-namespace",
        "-f", "docker-desktop.yml",
    ]  # fmt: skip
    values_overlay = VALUES_OVERLAYS[topology]
    if values_overlay:
        cmd += [
            "-f", values_overlay,
            "--set-file", "nginx.tls.crt=certs/tls.crt",
            "--set-file", "nginx.tls.key=certs/tls.key",
        ]  # fmt: skip
    for name in REQUIRED_ENV[surface]:
        if name in HELM_VALUE_FOR:
            cmd += ["--set-string", f"{HELM_VALUE_FOR[name]}={_config_value(surface_dir, name)}"]

    result = _run(cmd, surface_dir, timeout=900)
    if result.returncode != 0:
        pytest.fail(f"{surface}/{topology}: helm upgrade failed:\n{result.stdout}\n{result.stderr}")


def _ensure_certs(surface_dir: Path) -> Path:
    """Generate the demo CA and certificate if they are not already present."""
    ca_cert = surface_dir / "certs" / "ca.crt"
    if not ca_cert.exists():
        result = _run(["bash", "./generate-certs.sh"], surface_dir, timeout=600)
        if result.returncode != 0 or not ca_cert.exists():
            pytest.fail(f"generate-certs.sh failed for {surface_dir.name}:\n{result.stdout}\n{result.stderr}")
    return ca_cert


def _wait_until_serving(stack: Stack, timeout: float = 420.0) -> None:
    """Block until every component answers, not just the first one.

    The Compute Service becomes ready a few seconds after the Object Service,
    so waiting on one endpoint and then probing the others reports spurious
    502s.
    """
    deadline = time.monotonic() + timeout
    pending = list(stack.components)
    last_error = ""
    while pending and time.monotonic() < deadline:
        still_pending = []
        for component in pending:
            try:
                response = stack.get(component, HEALTH_PATHS[component], timeout=5)
                if response.status_code != 200:
                    last_error = f"{component} returned {response.status_code}"
                    still_pending.append(component)
            except requests.RequestException as exc:
                last_error = f"{component}: {type(exc).__name__}"
                still_pending.append(component)
        pending = still_pending
        if pending:
            time.sleep(3)
    if pending:
        pytest.fail(f"{stack.surface}/{stack.topology}: {', '.join(pending)} never became ready ({last_error})")


@pytest.fixture(scope="module")
def stack(request: pytest.FixtureRequest, surface: str, platform: str) -> object:
    """Bring up one deployment, yield it, and tear it down.

    The surface and platform come from the ``surface`` and ``platform``
    fixtures that each ``tests/<surface>/<platform>/`` directory defines; the
    topology comes from the test module's ``TOPOLOGY`` constant.
    """
    topology = request.module.TOPOLOGY
    surface_dir = REPO_ROOT / surface

    if platform == "kubernetes":
        _require_kubernetes()

    missing = [name for name in REQUIRED_ENV[surface] if not _config_value(surface_dir, name)]
    if missing:
        pytest.skip(f"not set in the environment or in {surface}/.env: {', '.join(missing)}")

    ca_cert = _ensure_certs(surface_dir) if topology != "http" else None

    _down_everything()

    if platform == "kubernetes":
        _helm_deploy(surface, surface_dir, topology)
    else:
        result = _run(_compose(surface_dir, topology, "up", "-d", "--build"), surface_dir)
        if result.returncode != 0:
            pytest.fail(f"{surface}/{topology}: compose up failed:\n{result.stdout}\n{result.stderr}")

    running = Stack(
        surface=surface,
        platform=platform,
        topology=topology,
        urls=URLS[surface, platform, topology],
        ca_cert=ca_cert,
    )
    try:
        _wait_until_serving(running)
        yield running
    finally:
        if request.config.getoption("--keep-stack"):
            print(f"\n--keep-stack: leaving {surface}/{platform}/{topology} running")
        elif platform == "kubernetes":
            _helm_uninstall()
        else:
            _run(_compose(surface_dir, topology, "down"), surface_dir, timeout=300)


def _config_value(surface_dir: Path, name: str) -> str:
    """Resolve one setting the way Docker Compose will resolve it.

    Compose takes the value from the environment when it is set there, and
    falls back to the surface's ``.env`` otherwise. This mirrors that order, so
    the tests skip exactly when the deployment would fail to start: locally
    that usually means ``.env``, while CI can export the variables instead and
    never create the file.
    """
    from_environment = os.environ.get(name, "").strip()
    if from_environment:
        return from_environment

    env_file = surface_dir / ".env"
    if not env_file.exists():
        return ""
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip()
    return ""
