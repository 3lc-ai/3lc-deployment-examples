# =============================================================================
# <copyright>
# Copyright (c) 2026 3LC Inc. All rights reserved.
#
# All rights are reserved. Reproduction or transmission in whole or in part, in
# any form or by any means, electronic, mechanical or otherwise, is prohibited
# without the prior written permission of the copyright owner.
# </copyright>
# =============================================================================
"""The deployment matrix: which components each surface serves, and where."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent

# Compose overlay per topology; None means the base file on its own.
OVERLAYS = {
    "http": None,
    "tls-per-host": "docker-compose.tls-per-host.yml",
    "tls-gateway": "docker-compose.tls-gateway.yml",
}

# Variables each surface needs in its .env. Missing ones skip rather than fail:
# the deployment cannot work without them and that is a machine setup problem,
# not a defect in the examples.
REQUIRED_ENV = {
    "default": ("TLC_API_KEY",),
    "enterprise-on-prem": (
        "TLC_PYPI_ACCESS_KEY",
        "TLC_PYPI_SECRET_KEY",
        "TLC_LICENSE",
        "TLC_OBJECT_SERVICE_AUTH_SECRET",
    ),
}

# Values overlay per topology for the Helm deployments; None means the
# docker-desktop overlay on its own.
VALUES_OVERLAYS = {
    "http": None,
    "tls-per-host": "tls-per-host-values.yaml",
    "tls-gateway": "tls-gateway-values.yaml",
}

# Base URL per component, for every surface, platform and topology. These are
# exactly the addresses the READMEs document, so a change that breaks a
# documented URL breaks these tests.
#
# The HTTPS addresses are the same on both platforms: Docker Desktop binds a
# LoadBalancer Service straight onto the host, so Kubernetes serves 443 just as
# Compose does. Only the plain-HTTP addresses differ, Compose publishing 8080
# and Kubernetes a NodePort on 30000.
_TLS_URLS = {
    ("default", "tls-per-host"): {
        "object_service": "https://object-service.localhost",
        "compute_service": "https://compute.localhost",
    },
    ("default", "tls-gateway"): {
        "object_service": "https://3lc.localhost",
        "compute_service": "https://3lc.localhost/compute",
    },
    ("enterprise-on-prem", "tls-per-host"): {
        "object_service": "https://object-service.localhost",
        "compute_service": "https://compute.localhost",
        "dashboard": "https://dashboard.localhost",
        "hub": "https://hub.localhost",
    },
    ("enterprise-on-prem", "tls-gateway"): {
        "object_service": "https://3lc.localhost/object-service",
        "compute_service": "https://3lc.localhost/compute",
        "dashboard": "https://3lc.localhost/dashboard",
        "hub": "https://3lc.localhost",
    },
}


def _http_urls(origin: str) -> dict[tuple[str, str], dict[str, str]]:
    return {
        ("default", "http"): {
            "object_service": origin,
            "compute_service": f"{origin}/compute",
        },
        ("enterprise-on-prem", "http"): {
            "object_service": f"{origin}/object-service",
            "compute_service": f"{origin}/compute",
            "dashboard": f"{origin}/dashboard",
            "hub": origin,
        },
    }


URLS: dict[tuple[str, str, str], dict[str, str]] = {
    (surface, platform, topology): urls
    for platform, http_origin in (("compose", "http://localhost:8080"), ("kubernetes", "http://localhost:30000"))
    for (surface, topology), urls in {**_http_urls(http_origin), **_TLS_URLS}.items()
}

PLATFORMS = ("compose", "kubernetes")

SURFACES = tuple(sorted({surface for surface, _, _ in URLS}))

# Unauthenticated endpoint that proves a component is serving.
HEALTH_PATHS = {
    "object_service": "/live",
    "compute_service": "/health",
    "dashboard": "/",
    "hub": "/",
}


@dataclass(frozen=True)
class Stack:
    """A running deployment, and how to reach its components."""

    surface: str
    platform: str
    topology: str
    urls: dict[str, str]
    ca_cert: Path | None

    @property
    def components(self) -> tuple[str, ...]:
        return tuple(self.urls)

    def url(self, component: str, path: str = "") -> str:
        return self.urls[component].rstrip("/") + path

    def get(self, component: str, path: str = "", **kwargs: object) -> requests.Response:
        """GET a path on one component, verifying TLS against the demo CA."""
        if self.ca_cert is not None:
            kwargs.setdefault("verify", str(self.ca_cert))
        kwargs.setdefault("timeout", 30)
        return requests.get(self.url(component, path), **kwargs)  # type: ignore[arg-type]
