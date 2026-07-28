#!/bin/bash
#=============================================================================
# <copyright>
# Copyright (c) 2024 3LC Inc. All rights reserved.
#
# All rights are reserved. Reproduction or transmission in whole or in part, in
# any form or by any means, electronic, mechanical or otherwise, is prohibited
# without the prior written permission of the copyright owner.
# </copyright>
#=============================================================================

set -e

# The kube-context to deploy into, defaulting to the local Docker Desktop cluster.
#
#   ./deploy.sh                deploy to docker-desktop
#   ./deploy.sh my-cluster     deploy to a named context instead
KUBE_CONTEXT="${1:-docker-desktop}"

if ! kubectl config get-contexts -o name | grep -qx "${KUBE_CONTEXT}"; then
  echo "error: kube-context '${KUBE_CONTEXT}' not found. Available contexts:" >&2
  kubectl config get-contexts -o name | sed 's/^/  /' >&2
  exit 1
fi

echo "Deploying to kube-context : ${KUBE_CONTEXT}"
echo "                  cluster : $(kubectl config view -o jsonpath="{.contexts[?(@.name=='${KUBE_CONTEXT}')].context.cluster}")"
echo "  (your current context is: $(kubectl config current-context))"
echo

# Deploy the chart. All subcharts are local, under helm/charts, so there is
# no chart repository to add and no dependencies to fetch.
helm upgrade -i tlc-demo ./helm \
  --kube-context "${KUBE_CONTEXT}" \
  --namespace tlc-demo --create-namespace \
  -f docker-desktop.yml
