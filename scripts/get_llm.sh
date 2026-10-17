#!/usr/bin/env bash
# Download IBM Granite 4.0 instruct GGUFs from Hugging Face and convert them to
# big-endian so llama.cpp can load them on IBM Z / LinuxONE (s390x).
# Run inside the lab container, from the project root:  bash scripts/get_llm.sh
set -euo pipefail
mkdir -p models/llm && cd models/llm
pip install -q --only-binary=:all: gguf

for m in granite-4.0-h-350m granite-4.0-h-1b; do
  out="$m-Q8_0-be.gguf"
  [ -f "$out" ] && { echo "$out exists"; continue; }
  curl -fL -o "$out" "https://huggingface.co/ibm-granite/$m-GGUF/resolve/main/$m-Q8_0.gguf"
  # GGUF files are little-endian; byte-swap tensors + metadata in place for s390x
  echo YES | python -m gguf.scripts.gguf_convert_endian "$out" big
done
ls -la
