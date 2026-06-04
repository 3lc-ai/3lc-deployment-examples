#=============================================================================
# <copyright>
# Copyright (c) 2024 3LC Inc. All rights reserved.
#
# All rights are reserved. Reproduction or transmission in whole or in part, in
# any form or by any means, electronic, mechanical or otherwise, is prohibited
# without the prior written permission of the copyright owner.
# </copyright>
#=============================================================================

# This can be any supported Python version. The Dashboard does not require any third party packages to serve the static contents.
FROM python:3.12

ARG ACCESS_KEY
ARG SECRET_KEY
ARG DASHBOARD_VERSION

# Upgrade pip first for a consistent, modern resolver across all 3LC images.
RUN pip install --no-cache --upgrade pip

RUN pip install --no-cache --index-url https://${ACCESS_KEY}:${SECRET_KEY}@pypi.3lc.ai/repositories/releases --extra-index-url https://pypi.org/simple 3lc-dashboard==${DASHBOARD_VERSION}

EXPOSE 8080

# Use this as the entrypoint so that docker compose's command override only needs to provide additional arguments.
# For Kubernetes, the command block needs to include everything anyway.
ENTRYPOINT [ "3lc-dashboard" ]
