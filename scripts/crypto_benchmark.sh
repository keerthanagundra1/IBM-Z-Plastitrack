#!/usr/bin/env bash
# Show IBM Z CPACF (on-chip crypto) acceleration on LinuxONE.
# Runs OpenSSL's benchmark twice: normally (CPACF used automatically) and with the
# CPACF instructions masked out via OPENSSL_s390xcap (pure software).
#   bash scripts/crypto_benchmark.sh
set -euo pipefail
NO_CPACF="km:0:0;kmc:0:0;kma:0:0;kmac:0:0;kmctr:0:0;kmo:0:0;kmf:0:0;kimd:0:0;klmd:0:0;pcc:0:0;kdsa:0:0;prno:0:0"

speed() {   # $1 = algorithm, prints throughput in MB/s for 16 KB blocks
  openssl speed -evp "$1" -seconds 2 -bytes 16384 2>/dev/null | tail -1 | awk '{v=$NF; sub("k","",v); printf "%.0f", v/1000}'
}

echo "CPU: $(uname -m) | CPACF facility: $(grep -o -m1 '\bmsa\b' /proc/cpuinfo || echo missing) | $(openssl version)"
printf "\n%-14s %16s %16s %10s\n" "algorithm" "CPACF on (MB/s)" "CPACF off (MB/s)" "speed-up"
for alg in aes-256-gcm aes-128-gcm sha256 sha512; do
  on=$(speed "$alg")
  off=$(OPENSSL_s390xcap="$NO_CPACF" speed "$alg")
  printf "%-14s %16s %16s %9.0fx\n" "$alg" "$on" "$off" "$(echo "$on / $off" | bc -l)"
done
echo -e "\nPlastiTrack's HTTPS (TLS 1.3, AES-256-GCM) and SSH tunnel use these CPACF instructions automatically."
