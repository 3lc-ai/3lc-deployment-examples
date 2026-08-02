# =============================================================================
# <copyright>
# Copyright (c) 2026 3LC Inc. All rights reserved.
#
# All rights are reserved. Reproduction or transmission in whole or in part, in
# any form or by any means, electronic, mechanical or otherwise, is prohibited
# without the prior written permission of the copyright owner.
# </copyright>
# =============================================================================
"""The Enterprise On-Prem surface on Kubernetes, over HTTPS with one hostname per component."""

from __future__ import annotations

import pytest

from tests.checks import DeploymentChecks, TlsPerHostChecks

TOPOLOGY = "tls-per-host"

pytestmark = [pytest.mark.kubernetes, pytest.mark.tls]


class TestTlsPerHost(DeploymentChecks, TlsPerHostChecks):
    """A LoadBalancer Service on 443, which Docker Desktop binds to the host."""
