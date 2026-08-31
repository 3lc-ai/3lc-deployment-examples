#=============================================================================
# <copyright>
# Copyright (c) 2026 3LC Inc. All rights reserved.
#
# All rights are reserved. Reproduction or transmission in whole or in part, in
# any form or by any means, electronic, mechanical or otherwise, is prohibited
# without the prior written permission of the copyright owner.
# </copyright>
#=============================================================================

# syntax=docker/dockerfile:1

# The python version should be 3.10 - 3.13.
FROM python:3.12

ARG TLC_HUB_FRONTEND_VERSION

# Upgrade pip first to avoid issues with old pip resolver.
RUN pip install --no-cache --upgrade pip

# The Hub frontend is published only to the private prereleases index, so unlike the
# Compute Service this build needs the private PyPI credentials.
#
# They arrive as build secrets, not build args. A build arg interpolated into a RUN
# line is recorded verbatim in the image's layer metadata, where `docker history` will
# show it to anyone holding the image. A secret mount exists only for the duration of
# this one RUN and is never written to a layer.
RUN --mount=type=secret,id=tlc_pypi_access_key,env=TLC_PYPI_ACCESS_KEY \
    --mount=type=secret,id=tlc_pypi_secret_key,env=TLC_PYPI_SECRET_KEY \
    pip install --no-cache \
      --index-url "https://${TLC_PYPI_ACCESS_KEY}:${TLC_PYPI_SECRET_KEY}@pypi.3lc.ai/repositories/releases" \
      --extra-index-url https://pypi.org/simple \
      "3lc-hub-frontend==${TLC_HUB_FRONTEND_VERSION}"

EXPOSE 8081

# The environment variables TLC_OBJECT_SERVICE_AUTH_SECRET, TLC_OBJECT_SERVICE_URL,
# TLC_COMPUTE_SERVICE_URL and TLC_DASHBOARD_URL should be set at run time. The three URLs
# are resolved by the browser, not by this container, so they must be addresses a browser
# can reach.
#
# The wheel serves the app with waitress and already binds 0.0.0.0 on port 8081, so no
# address or port override is needed here.
CMD ["3lc-hub-frontend"]
