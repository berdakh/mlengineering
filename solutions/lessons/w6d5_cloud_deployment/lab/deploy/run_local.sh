#!/usr/bin/env bash
# The local equivalent of the cloud deployment: same image, same environment variables, same health
# check command as deploy/taskdef.template.json, published on 127.0.0.1 only. Run from the lab dir.
#
#   bash deploy/run_local.sh                 # build, run, check /readyz and /version, remove
#   KEEP=1 bash deploy/run_local.sh          # leave it running (stop: docker rm -f flowguard-local)
#
# Behind a TLS-intercepting proxy (pip cannot verify PyPI from inside the build), fill
# service/wheels/ with `pip download` (see the lesson) and set
#   PIP_INSTALL_OPTS="--no-index --find-links=/srv/wheels"
set -euo pipefail
RELEASE="${FLOWGUARD_RELEASE:-$(git rev-parse --short=12 HEAD 2>/dev/null || echo 0000000)}"
IMAGE="flowguard:${RELEASE}"
NAME=flowguard-local
PORT="${PORT:-8000}"

docker build -q --build-arg PIP_INSTALL_OPTS="${PIP_INSTALL_OPTS:-}" -t "$IMAGE" service >/dev/null
docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" -p "127.0.0.1:${PORT}:8000" \
  -e FLOWGUARD_ENV=production -e FLOWGUARD_RELEASE="$RELEASE" \
  -e FLOWGUARD_MODEL_DIR=/models/flowguard-z/1.0.0 -e FLOWGUARD_PORT=8000 \
  --memory 512m --cpus 0.25 \
  --health-cmd "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=2)\" || exit 1" \
  --health-interval 15s --health-timeout 5s --health-retries 3 --health-start-period 20s \
  "$IMAGE" >/dev/null

for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${PORT}/readyz" >/dev/null 2>&1; then break; fi
  sleep 1
done
echo "readyz:  $(curl -sS "http://127.0.0.1:${PORT}/readyz")"
echo "version: $(curl -sS "http://127.0.0.1:${PORT}/version")"
docker logs "$NAME" 2>&1 | grep '"model_loaded"' | head -1
if [ -z "${KEEP:-}" ]; then docker rm -f "$NAME" >/dev/null && echo "removed container $NAME (image $IMAGE kept)"; fi
