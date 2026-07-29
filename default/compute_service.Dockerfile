#=============================================================================
# <copyright>
# Copyright (c) 2026 3LC Inc. All rights reserved.
#
# All rights are reserved. Reproduction or transmission in whole or in part, in
# any form or by any means, electronic, mechanical or otherwise, is prohibited
# without the prior written permission of the copyright owner.
# </copyright>
#=============================================================================

# The python version should be 3.10 - 3.13.
FROM python:3.12

ARG TLC_COMPUTE_VERSION

# Upgrade pip first to avoid issues with old pip resolver.
RUN pip install --no-cache --upgrade pip

# Three indexes are needed, in this order:
#   prereleases-public  the Compute Service itself, which has no release build yet
#   releases-public     its 3lc dependency
#   pypi.org            everything else
RUN pip install --no-cache \
    --index-url https://pypi.3lc.ai/public/repositories/prereleases-public \
    --extra-index-url https://pypi.3lc.ai/public/repositories/releases-public \
    --extra-index-url https://pypi.org/simple \
    3lc-compute==${TLC_COMPUTE_VERSION}

EXPOSE 5020

# The environment variable TLC_API_KEY should be set at run time.
# By default, it only binds to localhost. We need 0.0.0.0 so that traffic outside the container can be accepted.
CMD ["3lc-compute", "--host", "0.0.0.0", "--port", "5020"]
