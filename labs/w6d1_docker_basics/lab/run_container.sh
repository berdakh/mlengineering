#!/usr/bin/env bash
# Build the image and run the API locally - YOUR script (w6d1 guided lab).
#   ./run_container.sh            build, then run in the foreground (Ctrl+C stops it)
#   ./run_container.sh --detach   build, then run in the background
set -euo pipefail
cd "$(dirname "$0")"

# TODO 1: docker build this directory and tag the image flowguard:0.6.0
# TODO 2: docker run it with --rm and a name, publishing container port 8000 on the
#         LOOPBACK interface of this machine only (see the lesson: why not "-p 8000:8000"?)
echo "run_container.sh is not written yet" >&2
exit 1
