# =============================================================================
# <copyright>
# Copyright (c) 2026 3LC Inc. All rights reserved.
#
# All rights are reserved. Reproduction or transmission in whole or in part, in
# any form or by any means, electronic, mechanical or otherwise, is prohibited
# without the prior written permission of the copyright owner.
# </copyright>
# =============================================================================
"""The Default surface over plain HTTP."""

from __future__ import annotations

import pytest

from tests.checks import DeploymentChecks

TOPOLOGY = "http"

pytestmark = [pytest.mark.compose, pytest.mark.http]


class TestHttp(DeploymentChecks):
    """Everything is served over HTTP from a single port."""
