#!/bin/bash
#=============================================================================
# <copyright>
# Copyright (c) 2026 3LC Inc. All rights reserved.
#
# All rights are reserved. Reproduction or transmission in whole or in part, in
# any form or by any means, electronic, mechanical or otherwise, is prohibited
# without the prior written permission of the copyright owner.
# </copyright>
#=============================================================================

set -e

# Generates the certificates used by the TLS variants of this example.
#
# Produces a local certificate authority and one leaf certificate covering every
# hostname the example uses, so the same certificate serves both the single
# entry point and the per-component topologies.
#
# No public certificate authority can issue for these names: .localhost is not a
# real domain, so Let's Encrypt and friends have no way to validate ownership.
# Avoiding browser warnings therefore means trusting the CA generated here,
# which is a one-time step described in the README. In a real deployment you
# would drop in a certificate from your own PKI instead and skip this entirely.
#
# openssl runs in a container so there is nothing to install on the host.

CERT_DIR="$(cd "$(dirname "$0")" && pwd)/certs"
DAYS_CA=3650
DAYS_LEAF=825   # browsers reject leaf certificates valid for much longer

# Every name the example serves. The gateway topology uses the first one; the
# per-component topology uses the rest. This surface has no Dashboard or Hub of
# its own: those are hosted by 3LC and point at the services deployed here.
HOSTS=(
  3lc.localhost
  object-service.localhost
  compute.localhost
  localhost
)

mkdir -p "$CERT_DIR"

# On Windows under Git Bash, paths that look absolute get rewritten before docker
# sees them, which mangles both the mount target and -w. cygpath gives docker a
# native host path, and MSYS_NO_PATHCONV stops the container-side paths being
# touched. Both are no-ops elsewhere.
CERT_MOUNT="$CERT_DIR"
if command -v cygpath >/dev/null 2>&1; then
  CERT_MOUNT="$(cygpath -w "$CERT_DIR")"
  export MSYS_NO_PATHCONV=1
fi

SAN=""
for h in "${HOSTS[@]}"; do SAN="${SAN}DNS:${h},"; done
SAN="${SAN}IP:127.0.0.1"

echo "Generating a local CA and a leaf certificate for:"
for h in "${HOSTS[@]}"; do echo "  ${h}"; done
echo

# The image entrypoint is openssl itself, so override it to run the script below.
# Note the script arrives on the container's stdin, so openssl cannot also read
# from /dev/stdin; the extension file is written to disk instead.
docker run --rm -i -v "${CERT_MOUNT}:/certs" -w /certs --entrypoint sh alpine/openssl:latest -s <<EOF
set -e

# The certificate authority. Trust this once and every certificate below is accepted.
openssl req -x509 -newkey rsa:4096 -sha256 -days ${DAYS_CA} -nodes   -keyout ca.key -out ca.crt   -subj "/CN=3LC deployment examples local CA/O=3LC/OU=Examples"   -addext "basicConstraints=critical,CA:TRUE"   -addext "keyUsage=critical,keyCertSign,cRLSign"

cat > /tmp/leaf.ext <<EXT
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=${SAN}
EXT

# The certificate the proxy actually serves, signed by that CA.
openssl req -newkey rsa:2048 -sha256 -nodes   -keyout tls.key -out tls.csr   -subj "/CN=3lc.localhost/O=3LC/OU=Examples"

openssl x509 -req -in tls.csr -CA ca.crt -CAkey ca.key -CAcreateserial   -out tls.crt -days ${DAYS_LEAF} -sha256 -extfile /tmp/leaf.ext

rm -f tls.csr ca.srl
chmod 644 ca.crt tls.crt tls.key
EOF

echo "Wrote:"
echo "  ${CERT_DIR}/ca.crt   the CA to trust (see the README)"
echo "  ${CERT_DIR}/tls.crt  the certificate the proxy serves"
echo "  ${CERT_DIR}/tls.key  its private key"
