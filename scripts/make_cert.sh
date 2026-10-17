#!/usr/bin/env bash
# Create a self-signed TLS certificate (ECDSA P-256) for the PlastiTrack container.
# Files go to certs/ (git-ignored).  bash scripts/make_cert.sh
set -euo pipefail
mkdir -p certs
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes -days 30 \
  -subj "/CN=localhost/O=PlastiTrack" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" \
  -keyout certs/key.pem -out certs/cert.pem
chmod 644 certs/cert.pem certs/key.pem    # readable by the container's non-root user (uid 1000)
openssl x509 -in certs/cert.pem -noout -subject -enddate
