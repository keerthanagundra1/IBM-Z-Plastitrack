#!/usr/bin/env bash
# Copy the project from this laptop to LinuxONE (~/shared/plastitrack).
# ~/shared on the host is mounted into the lab "notebook" container at
# /home/ibm-user/shared, so the code is immediately runnable there.
#
# Usage (Git Bash / Linux / macOS):
#   LINUXONE_KEY=/path/to/key.pem ./scripts/sync_to_linuxone.sh
#
# Large folders (data/, models/) are NOT pushed — they are created on LinuxONE.
set -euo pipefail

HOST="${LINUXONE_HOST:-linux1@148.100.78.97}"
KEY="${LINUXONE_KEY:-/tmp/lx1.pem}"
REMOTE_DIR="shared/plastitrack"

cd "$(dirname "$0")/.."

tar czf - \
  --exclude=./data/raw --exclude=./data/processed --exclude=./models \
  --exclude=.git --exclude=__pycache__ --exclude=.ipynb_checkpoints \
  --exclude='*.pem' . \
| ssh -i "$KEY" -o BatchMode=yes "$HOST" \
  "mkdir -p ~/$REMOTE_DIR/{data/raw,data/processed,models} && tar xzf - -C ~/$REMOTE_DIR"

echo "Synced to $HOST:~/$REMOTE_DIR"
