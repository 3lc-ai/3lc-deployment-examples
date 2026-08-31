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

# The python version should be 3.10 - 3.13.
FROM python:3.12

ARG TLC_VERSION

# Upgrade pip first to avoid issues with old pip resolver.
RUN pip install --no-cache --upgrade pip

# The private PyPI credentials arrive as build secrets, not build args. A build arg
# interpolated into a RUN line is recorded verbatim in the image's layer metadata, where
# `docker history` will show it to anyone holding the image. A secret mount exists only
# for the duration of this one RUN and is never written to a layer.
RUN --mount=type=secret,id=tlc_pypi_access_key,env=TLC_PYPI_ACCESS_KEY \
    --mount=type=secret,id=tlc_pypi_secret_key,env=TLC_PYPI_SECRET_KEY \
    pip install --no-cache \
      "3lc==${TLC_VERSION}"

EXPOSE 5015

# The environment variables TLC_LICENSE and TLC_OBJECT_SERVICE_AUTH_SECRET should be set at run time.
# Since this runs as a background service, tui is not needed.
# By default, it only binds to localhost. We need 0.0.0.0 so that traffic outside the container can be accepted.
CMD ["3lc", "service", "--no-tui", "--host", "0.0.0.0"]