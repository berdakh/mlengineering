#!/usr/bin/env bash
# Build the image and run the API locally - REFERENCE SOLUTION (w6d1).
#   ./run_container.sh            build, then run in the foreground (Ctrl+C stops it)
#   ./run_container.sh --detach   build, then run in the background (stop with: docker stop flowguard)
set -euo pipefail
cd "$(dirname "$0")"
IMAGE="${IMAGE:-flowguard:0.6.0}"
NAME="${NAME:-flowguard}"
PORT="${PORT:-8000}"

docker build -t "$IMAGE" .

MODE=()
if [[ "${1:-}" == "--detach" ]]; then MODE=(--detach); fi

# -p 127.0.0.1:PORT:8000 publishes on the loopback interface only: reachable from this machine,
# not from the network. A bare "-p 8000:8000" listens on every interface and bypasses ufw.
docker run "${MODE[@]}" --rm --name "$NAME" -p "${PORT}:8000" "$IMAGE"
