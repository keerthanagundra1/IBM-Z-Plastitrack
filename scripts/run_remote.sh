#!/usr/bin/env bash
# Run a command inside the lab "notebook" container on LinuxONE,
# from the project folder (/home/ibm-user/shared/plastitrack).
#
# Usage:
#   ./scripts/run_remote.sh python scripts/check_env.py
#   ./scripts/run_remote.sh "grep acc reports/train.log | head"
set -euo pipefail

HOST="${LINUXONE_HOST:-linux1@148.100.78.97}"
KEY="${LINUXONE_KEY:-/tmp/lx1.pem}"

# The command goes in over stdin, so quotes and pipes in it need no escaping.
echo "$*" | ssh -i "$KEY" -o BatchMode=yes "$HOST" \
  "docker exec -i -w /home/ibm-user/shared/plastitrack notebook bash -l"
