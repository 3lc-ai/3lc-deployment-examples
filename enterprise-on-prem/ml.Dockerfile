#=============================================================================
# <copyright>
# Copyright (c) 2024 3LC Inc. All rights reserved.
#
# All rights are reserved. Reproduction or transmission in whole or in part, in
# any form or by any means, electronic, mechanical or otherwise, is prohibited
# without the prior written permission of the copyright owner.
# </copyright>
#=============================================================================

# This is to show that 3LC needs to be installed with the node that will be running the ML workload.
# This allows the ML workload to use the 3LC library to improve training quality.
# For the purpose of the demo, we use JupyterLab so that we can see and do the ML workload in Jupyter notebooks.
FROM jupyter/base-notebook

ARG ACCESS_KEY
ARG SECRET_KEY
ARG TLC_VERSION

# Upgrade pip first to avoid issues with old pip resolver.
RUN pip install --no-cache --upgrade pip

# Install 3LC
RUN pip install --no-cache --index-url https://${ACCESS_KEY}:${SECRET_KEY}@pypi.3lc.ai/repositories/releases --extra-index-url https://pypi.org/simple 3lc==${TLC_VERSION}

# Install other ML stuff

# For this demo, jupyter will run at port 8888