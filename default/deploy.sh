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

# The API key lives in .env, which is where Part 1 already keeps it. Kubernetes
# does not read that file, so pass it to Helm explicitly rather than having it
# typed into docker-desktop.yml, which is tracked by git.
#
# Sourcing is conditional so an already-exported variable, or a secret injected
# by CI, works just as well.
ENV_FILE="$(cd "$(dirname "$0")" && pwd)/.env"
if [ -f "${ENV_FILE}" ]; then
  set -a
  . "${ENV_FILE}"
  set +a
fi

: "${TLC_API_KEY:?is not set. Copy .env.example to .env and fill it in, or export it before running this script.}"

# Deploy the chart. All subcharts are local, under helm/charts, so there is
# no chart repository to add and no dependencies to fetch.
helm upgrade -i tlc-demo ./helm \
  --kube-context "${KUBE_CONTEXT}" \
  --namespace tlc-demo --create-namespace \
  -f docker-desktop.yml \
  --set-string global.apiKey="${TLC_API_KEY}"
