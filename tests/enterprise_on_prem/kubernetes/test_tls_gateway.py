# =============================================================================
# <copyright>
# Copyright (c) 2026 3LC Inc. All rights reserved.
#
# All rights are reserved. Reproduction or transmission in whole or in part, in
# any form or by any means, electronic, mechanical or otherwise, is prohibited
# without the prior written permission of the copyright owner.
# </copyright>
# =============================================================================
"""The Enterprise On-Prem surface on Kubernetes, over HTTPS behind a single hostname."""

from __future__ import annotations

import pytest

from tests.checks import DeploymentChecks, TlsGatewayChecks

TOPOLOGY = "tls-gateway"

pytestmark = [pytest.mark.kubernetes, pytest.mark.tls]


class TestTlsGateway(DeploymentChecks, TlsGatewayChecks):
    """A LoadBalancer Service on 443, routing every component by path."""
