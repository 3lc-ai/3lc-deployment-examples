# =============================================================================
# <copyright>
# Copyright (c) 2026 3LC Inc. All rights reserved.
#
# All rights are reserved. Reproduction or transmission in whole or in part, in
# any form or by any means, electronic, mechanical or otherwise, is prohibited
# without the prior written permission of the copyright owner.
# </copyright>
# =============================================================================
"""The Default surface over HTTPS, with one hostname per component."""

from __future__ import annotations

import pytest

from tests.checks import ComposeTlsPerHostChecks, DeploymentChecks, TlsPerHostChecks

TOPOLOGY = "tls-per-host"

pytestmark = [pytest.mark.compose, pytest.mark.tls]


class TestTlsPerHost(DeploymentChecks, TlsPerHostChecks, ComposeTlsPerHostChecks):
    """Each component owns an origin, so nothing is served under a prefix."""
