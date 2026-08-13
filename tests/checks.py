# =============================================================================
# <copyright>
# Copyright (c) 2026 3LC Inc. All rights reserved.
#
# All rights are reserved. Reproduction or transmission in whole or in part, in
# any form or by any means, electronic, mechanical or otherwise, is prohibited
# without the prior written permission of the copyright owner.
# </copyright>
# =============================================================================
"""The assertions, shared by every surface and topology.

Test modules under ``tests/<surface>/`` subclass these, which is what keeps a
check written once and run everywhere. ``DeploymentChecks`` applies to every
deployment; the two mixins add what is specific to a TLS topology. The module
sits outside ``test_*.py`` so the classes are not collected here as well.
"""

from __future__ import annotations

import pytest
import requests

from tests.deployments import Stack

# Hub pages reachable from its own navigation. They are absolute links, so they
# only resolve when the Hub owns the root of its origin.
HUB_PAGES = ("/projects", "/queue", "/settings/", "/settings/plugins", "/gettingstarted/")


class DeploymentChecks:
    """Assertions applied to every surface and topology."""

    def test_object_service_is_live(self, stack: Stack) -> None:
        response = stack.get("object_service", "/live")
        assert response.status_code == 200
        assert response.text.strip() == "OK"

    def test_object_service_requires_authentication(self, stack: Stack) -> None:
        """Everything but the health check is authenticated; 403 is correct."""
        response = stack.get("object_service", "/")
        assert response.status_code == 403

    def test_compute_service_is_healthy(self, stack: Stack) -> None:
        response = stack.get("compute_service", "/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["service"] == "3lc-compute"

    def test_paths_without_a_trailing_slash_stay_on_the_same_port(self, stack: Stack) -> None:
        """A component reached by path prefix must redirect back to itself.

        nginx adds the missing slash with a redirect it builds from the port it
        listens on, which is not the port the caller used once the deployment is
        behind a published port or a NodePort. Left absolute, the READMEs' own
        URLs send a browser to a port nothing serves.
        """
        for component in stack.components:
            base = stack.url(component)
            if base.count("/") < 3:  # a bare origin has no path prefix to strip
                continue
            response = requests.get(base, allow_redirects=False, **stack.request_kwargs())
            if response.status_code not in (301, 302):
                continue
            location = response.headers["location"]
            assert location.startswith("/"), f"{component}: redirect is absolute: {location}"

    def test_dashboard_loads(self, stack: Stack) -> None:
        if "dashboard" not in stack.components:
            pytest.skip(f"{stack.surface} does not deploy the Dashboard")
        response = stack.get("dashboard", "/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Identifies the Dashboard specifically: a proxy that routed this path
        # to another component would still return 200.
        assert "<title>3LC Dashboard</title>" in response.text

    def test_hub_loads(self, stack: Stack) -> None:
        if "hub" not in stack.components:
            pytest.skip(f"{stack.surface} does not deploy the Hub")
        response = stack.get("hub", "/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "<title>3LC Hub" in response.text

    def test_hub_navigation_resolves(self, stack: Stack) -> None:
        """The Hub's own links must work, since it emits them as absolute paths."""
        if "hub" not in stack.components:
            pytest.skip(f"{stack.surface} does not deploy the Hub")
        failures = {}
        for page in HUB_PAGES:
            status = stack.get("hub", page).status_code
            if status != 200:
                failures[page] = status
        assert not failures, f"Hub pages did not resolve: {failures}"


class TlsPerHostChecks:
    """Specific to the topology that gives each component its own hostname."""

    def test_every_component_has_its_own_origin(self, stack: Stack) -> None:
        origins = {stack.url(component).split("/", 3)[2] for component in stack.components}
        assert len(origins) == len(stack.components), f"components share an origin: {origins}"


class TlsGatewayChecks:
    """Specific to the topology that fronts everything with one hostname."""

    def test_every_component_shares_one_origin(self, stack: Stack) -> None:
        origins = {stack.url(component).split("/", 3)[2] for component in stack.components}
        assert origins == {"3lc.localhost"}


# The HTTPS deployments keep port 80 published under Compose and redirect from
# it. On Kubernetes the Service is a LoadBalancer on 443 alone, so there is no
# port-80 listener to redirect and these do not apply.
class ComposeTlsPerHostChecks:
    """Compose-only, for the topology with one hostname per component."""

    def test_plain_http_redirects_to_the_same_hostname(self, stack: Stack) -> None:
        """Port 8080 stays published and sends callers to the HTTPS site.

        The redirect preserves the hostname, which is the point here: each
        component keeps its own origin rather than being funnelled to one.
        """
        response = requests.get("http://object-service.localhost:8080/live", allow_redirects=False, timeout=30)
        assert response.status_code == 302
        assert response.headers["location"] == "https://object-service.localhost/live"

    def test_plain_http_does_not_redirect_other_names(self, stack: Stack) -> None:
        """A name this topology does not serve is refused, not redirected.

        Redirecting it would send the caller to a component that happens to be
        first in the config, and a browser would remember the redirect.
        """
        response = requests.get("http://localhost:8080/", allow_redirects=False, timeout=30)
        assert response.status_code == 404


class ComposeTlsGatewayChecks:
    """Compose-only, for the topology behind a single hostname."""

    def test_plain_http_redirects_to_https(self, stack: Stack) -> None:
        response = requests.get("http://3lc.localhost:8080/", allow_redirects=False, timeout=30)
        assert response.status_code == 302
        assert response.headers["location"] == "https://3lc.localhost/"

    def test_plain_http_does_not_redirect_other_names(self, stack: Stack) -> None:
        """Only the gateway hostname is redirected; anything else is refused."""
        response = requests.get("http://localhost:8080/", allow_redirects=False, timeout=30)
        assert response.status_code == 404
