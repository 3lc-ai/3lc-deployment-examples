# =============================================================================
# <copyright>
# Copyright (c) 2026 3LC Inc. All rights reserved.
#
# All rights are reserved. Reproduction or transmission in whole or in part, in
# any form or by any means, electronic, mechanical or otherwise, is prohibited
# without the prior written permission of the copyright owner.
# </copyright>
# =============================================================================
"""Every deployment under this directory runs on Docker Compose."""

from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def platform() -> str:
    return "compose"
