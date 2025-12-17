#=============================================================================
# <copyright>
# Copyright (c) 2024 3LC Inc. All rights reserved.
#
# All rights are reserved. Reproduction or transmission in whole or in part, in
# any form or by any means, electronic, mechanical or otherwise, is prohibited
# without the prior written permission of the copyright owner.
# </copyright>
#=============================================================================

#!/bin/bash
set -e

helm repo add bitnami https://charts.bitnami.com/bitnami
helm dependency build ./helm
helm upgrade -i tlc-demo ./helm --namespace tlc-demo --create-namespace -f docker-desktop.yml