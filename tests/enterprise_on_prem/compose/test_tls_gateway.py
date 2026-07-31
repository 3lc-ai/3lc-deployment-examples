# =============================================================================
# <copyright>
# Copyright (c) 2026 3LC Inc. All rights reserved.
#
# All rights are reserved. Reproduction or transmission in whole or in part, in
# any form or by any means, electronic, mechanical or otherwise, is prohibited
# without the prior written permission of the copyright owner.
# </copyright>
# =============================================================================
"""The Enterprise On-Prem surface over HTTPS, behind a single hostname."""

from __future__ import annotations

import pytest

from tests.checks import ComposeTlsGatewayChecks, DeploymentChecks, TlsGatewayChecks

TOPOLOGY = "tls-gateway"

pytestmark = [pytest.mark.compose, pytest.mark.tls]


class TestTlsGateway(DeploymentChecks, TlsGatewayChecks, ComposeTlsGatewayChecks):
    """One hostname fronts every component, routed by path."""
