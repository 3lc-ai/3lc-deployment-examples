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

# The license key and auth secret live in .env, which is where Part 1 already
# keeps them. Kubernetes does not read that file, so pass them to Helm
# explicitly rather than having them typed into docker-desktop.yml, which is
# tracked by git. The PyPI keys are not needed here: they are build-time only.
#
# Sourcing is conditional so already-exported variables, or secrets injected by
# CI, work just as well.
ENV_FILE="$(cd "$(dirname "$0")" && pwd)/.env"
if [ -f "${ENV_FILE}" ]; then
  set -a
  . "${ENV_FILE}"
  set +a
fi

: "${TLC_LICENSE:?is not set. Copy .env.example to .env and fill it in, or export it before running this script.}"
: "${TLC_OBJECT_SERVICE_AUTH_SECRET:?is not set. Copy .env.example to .env and fill it in, or export it before running this script.}"

# Deploy the chart. All subcharts are local, under helm/charts, so there is
# no chart repository to add and no dependencies to fetch.
helm upgrade -i tlc-demo ./helm \
  --kube-context "${KUBE_CONTEXT}" \
  --namespace tlc-demo --create-namespace \
  -f docker-desktop.yml \
  --set-string global.licenseKey="${TLC_LICENSE}" \
  --set-string global.objectServiceAuthSecret="${TLC_OBJECT_SERVICE_AUTH_SECRET}"
