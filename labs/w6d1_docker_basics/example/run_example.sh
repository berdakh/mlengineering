#!/usr/bin/env bash
# Worked example (w6d1): build the clock service twice, run each version, measure `docker stop`.
#   bash labs/w6d1_docker_basics/example/run_example.sh
# Needs a Docker daemon. Creates images clock:naive and clock:good and removes all containers it
# starts. Extra build options (proxy, CA) can be passed in DOCKER_BUILD_ARGS.
set -euo pipefail
cd "$(dirname "$0")/clock"
build_args=(${DOCKER_BUILD_ARGS:-})

docker build -q "${build_args[@]}" -f Dockerfile.naive -t clock:naive . >/dev/null
docker build -q "${build_args[@]}" -f Dockerfile -t clock:good . >/dev/null

measure() {   # $1 label, $2 image, rest: extra docker run options
  local label=$1 image=$2; shift 2
  docker run -d --rm --name clock-demo -p 127.0.0.1:8080:8080 "$@" "$image" >/dev/null
  for _ in $(seq 1 40); do curl -sf http://127.0.0.1:8080/health >/dev/null && break; sleep 0.25; done
  local body pid1 user start end
  body=$(curl -s http://127.0.0.1:8080/)
  pid1=$(docker exec clock-demo sh -c 'tr "\0" " " < /proc/1/cmdline')
  user=$(docker exec clock-demo id -un)
  start=$(date +%s.%N); docker stop clock-demo >/dev/null; end=$(date +%s.%N)
  printf '%-34s stop %5.2f s   user %-6s PID 1: %s\n' "$label" "$(echo "$end - $start" | bc)" "$user" "$pid1"
  echo "    GET / -> $body"
}

measure "naive (shell form, root)"         clock:naive
measure "good (exec form, handler)"        clock:good
measure "good image, handler switched off" clock:good -e CLOCK_HANDLE_SIGTERM=0
docker image ls --format '{{.Repository}}:{{.Tag}}  {{.Size}}' | grep '^clock:'
