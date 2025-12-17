#=============================================================================
# <copyright>
# Copyright (c) 2024 3LC Inc. All rights reserved.
#
# All rights are reserved. Reproduction or transmission in whole or in part, in
# any form or by any means, electronic, mechanical or otherwise, is prohibited
# without the prior written permission of the copyright owner.
# </copyright>
#=============================================================================

# The python version should be 3.9 - 3.13.
FROM python:3.11

ARG TLC_VERSION

# Install 3LC
RUN pip install --no-cache 3lc==${TLC_VERSION}

EXPOSE 5015

# The environment variable TLC_API_KEY should be set at run time.
# Since this runs as a background service, tui is not needed.
# By default, it only binds to localhost. We need 0.0.0.0 so that traffic outside the container can be accepted.
CMD ["3lc", "service", "--no-tui", "--host", "0.0.0.0"]