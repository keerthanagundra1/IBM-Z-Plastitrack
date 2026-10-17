#!/usr/bin/env bash
# Build and run the PlastiTrack container ON LINUXONE (run this on the LinuxONE host,
# from ~/shared/plastitrack).
#
#   ./scripts/container.sh build     # docker build
#   ./scripts/container.sh run       # start hardened container on 127.0.0.1:8501
#   ./scripts/container.sh status    # running container, health, security settings
#   ./scripts/container.sh stop
set -euo pipefail
IMAGE=plastitrack:1.0
NAME=plastitrack

case "${1:-}" in
  build)
    docker build -t "$IMAGE" .
    ;;
  run)
    docker rm -f "$NAME" >/dev/null 2>&1 || true
    # Security hardening:
    #   127.0.0.1 only (reach it through an SSH tunnel), non-root user, read-only root FS,
    #   all Linux capabilities dropped, no privilege escalation, CPU / memory / process limits.
    docker run -d --name "$NAME" \
      -p 127.0.0.1:8501:8501 \
      --user 1000:1000 \
      --read-only --tmpfs /tmp:rw,size=256m \
      --cap-drop ALL --security-opt no-new-privileges:true \
      --memory 3g --cpus 2 --pids-limit 256 \
      --restart unless-stopped \
      "$IMAGE"
    echo "Started. From your laptop: ssh -i <key.pem> -L 8501:localhost:8501 linux1@<linuxone-ip>"
    echo "Then open http://localhost:8501"
    ;;
  status)
    docker ps --filter "name=$NAME" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
    docker inspect "$NAME" --format \
      'user={{.Config.User}}  read-only={{.HostConfig.ReadonlyRootfs}}  cap-drop={{.HostConfig.CapDrop}}  security-opt={{.HostConfig.SecurityOpt}}  memory={{.HostConfig.Memory}}  cpus={{.HostConfig.NanoCpus}}  arch={{.Platform}}'
    docker exec "$NAME" python -c "import platform,sys,urllib.request; print('container arch:', platform.machine(), sys.byteorder); print(urllib.request.urlopen('http://127.0.0.1:8501/health').read().decode())"
    docker stats --no-stream "$NAME"
    ;;
  stop)
    docker rm -f "$NAME"
    ;;
  *)
    echo "usage: $0 {build|run|status|stop}"; exit 1 ;;
esac
