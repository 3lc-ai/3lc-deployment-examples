#=============================================================================
# <copyright>
# Copyright (c) 2024 3LC Inc. All rights reserved.
#
# All rights are reserved. Reproduction or transmission in whole or in part, in
# any form or by any means, electronic, mechanical or otherwise, is prohibited
# without the prior written permission of the copyright owner.
# </copyright>
#=============================================================================

# syntax=docker/dockerfile:1

# This can be any supported Python version. The Dashboard does not require any third party packages to serve the static contents.
FROM python:3.12

ARG DASHBOARD_VERSION

# Upgrade pip first to avoid issues with old pip resolver.
RUN pip install --no-cache --upgrade pip

# Install the 3lc-dashboard package.
# Use build secrets for the private PyPI credentials so they are not recorded in the
# image's layer metadata.
RUN --mount=type=secret,id=tlc_pypi_access_key,env=TLC_PYPI_ACCESS_KEY \
    --mount=type=secret,id=tlc_pypi_secret_key,env=TLC_PYPI_SECRET_KEY \
    pip install --no-cache \
      --index-url "https://${TLC_PYPI_ACCESS_KEY}:${TLC_PYPI_SECRET_KEY}@pypi.3lc.ai/repositories/releases" \
      --extra-index-url https://pypi.org/simple \
      "3lc-dashboard==${DASHBOARD_VERSION}"

EXPOSE 8080

# Use this as the entrypoint so that docker compose's command override only needs to provide additional arguments.
# For Kubernetes, the command block needs to include everything anyway.
ENTRYPOINT [ "3lc-dashboard" ]
